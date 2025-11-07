# middleware.py
"""
Django middleware for protecting /secure/api/* endpoints with AWS Cognito AccessTokens.
Temp workaround while waiting for a domain and cert so HTTPS can be configured on ALB.
ALB would then be responsible for validating the auth token.
"""
import json
import logging
import os
from typing import Optional

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

import jwt
from jwt import PyJWKClient, InvalidTokenError

logger = logging.getLogger(__name__)

class CognitoAccessTokenMiddleware(MiddlewareMixin):
    """Protects SECURE_API_PREFIX routes using Cognito AccessToken verification."""

    _jwks_client: Optional[PyJWKClient] = None
    _issuer: Optional[str] = None

    @staticmethod
    def _bool(val: Optional[str]) -> bool:
        return str(val or '').lower() in ('1', 'true', 'yes', 'y')

    def _cfg(self):
        region = os.getenv('AWS_REGION')
        user_pool_id = os.getenv('COGNITO_USER_POOL_ID') or os.getenv('COGNITO_USERPOOL_ID')
        audience = os.getenv('COGNITO_CLIENT_ID')  # App Client ID
        prefix = os.getenv('SECURE_API_PREFIX', '/secure/api')
        allow_insecure = self._bool(os.getenv('ALLOW_INSECURE_API'))
        rid_header = os.getenv('REQUEST_ID_HEADER')

        missing = []
        if not region: missing.append('AWS_REGION')
        if not user_pool_id: missing.append('COGNITO_USER_POOL_ID')
        if not audience: missing.append('COGNITO_CLIENT_ID')

        issuer = None
        jwks_client = self._jwks_client
        if region and user_pool_id:
            issuer = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}'
            # Lazy-init JWKS client once
            if jwks_client is None:
                jwks_url = f'{issuer}/.well-known/jwks.json'
                jwks_client = PyJWKClient(jwks_url)
                self._jwks_client = jwks_client
                self._issuer = issuer

        return {
            'region': region,
            'user_pool_id': user_pool_id,
            'audience': audience,
            'prefix': prefix.rstrip('/'),
            'allow_insecure': allow_insecure,
            'rid_header': rid_header,
            'missing': missing,
            'issuer': issuer,
            'jwks_client': jwks_client,
        }

    def _json(self, status: int, message: str, request):
        payload = {'error': message}
        rid_header = os.getenv('REQUEST_ID_HEADER')
        headers = {}
        if rid_header:
            rid = request.headers.get(rid_header)
            if rid:
                headers[rid_header] = rid
                payload['request_id'] = rid
        return JsonResponse(payload, status=status, headers=headers)

    def process_request(self, request):
        cfg = self._cfg()
        path = request.path

        # Skip non-secure routes
        if not path.startswith(cfg['prefix'] + '/') and path != cfg['prefix']:
            return None

        # Skip CORS preflight
        if request.method == 'OPTIONS':
            return None

        # Allow insecure in dev if enabled
        if cfg['allow_insecure']:
            return None

        # Ensure config present
        if cfg['missing']:
            msg = 'Server auth not configured: missing ' + ', '.join(cfg['missing'])
            logger.error(msg)
            return self._json(500, 'Server auth not configured', request)

        # Extract Bearer token
        auth = request.META.get('HTTP_AUTHORIZATION') or ''
        if not auth.lower().startswith('bearer '):
            return self._json(401, 'Missing Bearer token', request)
        token = auth.split(' ', 1)[1].strip()
        if not token:
            return self._json(401, 'Missing Bearer token', request)

        # Verify JWT (AccessToken)
        try:
            signing_key = cfg['jwks_client'].get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=['RS256'],
                issuer=cfg['issuer'],
                options={'verify_aud': False},  # AccessToken typically has no 'aud'
            )

            # Enforce AccessToken semantics
            if claims.get('token_use') != 'access':
                return self._json(401, "Invalid token_use (expected 'access')", request)

            # Enforce App Client match via client_id
            expected_client_id = cfg['audience']
            if claims.get('client_id') != expected_client_id:
                return self._json(401, 'Invalid client_id', request)

            # Optionally expose username on request
            request.user_username = (
                claims.get('username') or
                claims.get('cognito:username') or
                claims.get('sub')
            )

        except InvalidTokenError as e:
            logger.warning('Token invalid: %s', e)
            return self._json(401, f'invalid token: {e}', request)
        except Exception as e:
            # Any unexpected verification failure → 401 (not 500)
            logger.exception('Token validation error')
            return self._json(401, f'invalid token: {e}', request)

        # Auth OK → continue
        return None
