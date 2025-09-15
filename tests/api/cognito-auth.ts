// tests/api/cognito-auth.ts
import { CognitoIdentityProviderClient, InitiateAuthCommand } from "@aws-sdk/client-cognito-identity-provider";

export async function getAccessTokenWithPassword(): Promise<string> {
  const region = process.env.AWS_REGION || "eu-west-2";
  const clientId = process.env.COGNITO_CLIENT_ID!;
  const username = process.env.COGNITO_USERNAME!;
  const password = process.env.COGNITO_PASSWORD!;

  const client = new CognitoIdentityProviderClient({ region });
  const res = await client.send(new InitiateAuthCommand({
    AuthFlow: "USER_PASSWORD_AUTH",
    ClientId: clientId,
    AuthParameters: { USERNAME: username, PASSWORD: password },
  }));

  const token = res.AuthenticationResult?.AccessToken;
  if (!token) throw new Error("No access token from Cognito");
  return token;
}
