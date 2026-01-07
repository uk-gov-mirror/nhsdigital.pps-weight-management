import { test, expect, Page } from '@playwright/test';

/**
 * Pilot Access E2E Tests
 * 
 * These tests cover the gated entry system including:
 * - Landing page with campaign codes
 * - Registration flow
 * - Login flow
 * - User enumeration prevention
 * - Account management
 * - Logout and session handling
 * 
 * Prerequisites:
 * - Django app running with DEBUG=True (so OTP is visible on verify page)
 * - A valid campaign must exist in the database
 * 
 * Environment variables:
 * - DJANGO_BASE_URL: Base URL of the Django app
 * - TEST_CAMPAIGN_CODE: Valid campaign code for testing
 */

// Test configuration from environment
// Default 999999 matches the campaign code in v3_testdata.json fixture
const VALID_CAMPAIGN_CODE = process.env.TEST_CAMPAIGN_CODE || '999999';

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Generate unique test email.
 */
function generateTestEmail(prefix: string = 'test'): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substring(7)}@example.com`;
}

/**
 * Generate unique test phone.
 */
function generateTestPhone(): string {
  const random = Math.floor(Math.random() * 100000).toString().padStart(5, '0');
  return `07987${random}`;
}

/**
 * Extract OTP from the debug display on the OTP verify page.
 * Only works when DEBUG=True in Django settings.
 */
async function getDebugOTP(page: Page): Promise<string | null> {
  try {
    const otpElement = page.locator('.nhsuk-warning-callout strong');
    if (await otpElement.isVisible({ timeout: 3000 })) {
      const otpText = await otpElement.textContent();
      return otpText?.trim() || null;
    }
  } catch {
    // Element not found or not visible
  }
  return null;
}

/**
 * Complete the campaign signup flow up to OTP verification.
 */
async function signupWithCampaign(
  page: Page,
  campaignCode: string,
  email: string,
  phone: string,
  preferredMethod: 'email' | 'sms' = 'email'
): Promise<void> {
  // Go to landing with campaign code
  await page.goto(`/pilot/landing/?cc=${campaignCode}`);
  
  // Accept disclaimer
  await page.locator('#accept').check();
  await page.locator('button[type="submit"]').click();
  
  // Fill contact info
  await page.waitForURL(/\/pilot\/contact-info\//);
  await page.locator('#emailInput').fill(email);
  await page.locator('#phoneInput').fill(phone);
  await page.locator('#preferredContact').selectOption(preferredMethod);
  await page.locator('button[type="submit"]').click();
  
  // Should be on OTP verify page
  await page.waitForURL(/\/pilot\/otp\//);
}

/**
 * Complete OTP verification using the debug OTP display.
 */
async function verifyOTP(page: Page): Promise<boolean> {
  const otp = await getDebugOTP(page);
  if (!otp) {
    console.warn('Could not extract OTP from page. Is DEBUG=True?');
    return false;
  }
  
  await page.locator('#otp').fill(otp);
  await page.locator('button[type="submit"]').click();
  
  // Wait for redirect
  try {
    await page.waitForURL('/', { timeout: 5000 });
    return true;
  } catch {
    return false;
  }
}

/**
 * Login with email or phone.
 */
async function login(page: Page, contact: string): Promise<void> {
  await page.goto('/pilot/login/');
  await page.locator('#contact').fill(contact);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(/\/pilot\/otp\//);
}

/**
 * Logout the current user.
 */
async function logout(page: Page): Promise<void> {
  const logoutLink = page.locator('.nhsuk-header__account-link[href="/pilot/logout/"]');
  if (await logoutLink.isVisible()) {
    await logoutLink.click();
    await page.waitForURL(/\/pilot\/landing\//);
  }
}

/**
 * Create and authenticate a test user.
 */
async function createAuthenticatedUser(page: Page): Promise<{ email: string; phone: string }> {
  const email = generateTestEmail('auth');
  const phone = generateTestPhone();
  
  await signupWithCampaign(page, VALID_CAMPAIGN_CODE, email, phone, 'email');
  const success = await verifyOTP(page);
  
  if (!success) {
    throw new Error('Failed to create authenticated user - OTP verification failed');
  }
  
  return { email, phone };
}

// ============================================================================
// Landing Page Tests
// ============================================================================

test.describe('Landing Page', () => {
  test('shows login option when no campaign code provided', async ({ page }) => {
    await page.goto('/pilot/landing/');
    
    await expect(page.locator('h1')).toContainText(/Pilot site/i);
    await expect(page.locator('body')).toContainText(/Already accepted/i);
    await expect(page.locator('a[href="/pilot/login/"]')).toBeVisible();
  });

  test('shows disclaimer form with valid campaign code', async ({ page }) => {
    await page.goto(`/pilot/landing/?cc=${VALID_CAMPAIGN_CODE}`);
    
    await expect(page.locator('body')).toContainText(/beta disclaimer/i);
    await expect(page.locator('#accept')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('shows invalid message with invalid campaign code', async ({ page }) => {
    await page.goto('/pilot/landing/?cc=INVALID');
    
    await expect(page.locator('body')).toContainText(/Invalid campaign code/i);
    await expect(page.locator('#accept')).not.toBeVisible();
  });

  test('disclaimer checkbox is required', async ({ page }) => {
    await page.goto(`/pilot/landing/?cc=${VALID_CAMPAIGN_CODE}`);
    
    // Try to submit without checking the checkbox
    await page.locator('button[type="submit"]').click();
    
    // Should still be on landing page with error
    await expect(page).toHaveURL(/\/pilot\/landing\//);
    await expect(page.locator('.nhsuk-error-summary')).toBeVisible();
  });
});

// ============================================================================
// Authentication Gating Tests
// ============================================================================

test.describe('Authentication Gating', () => {
  test('unauthenticated user is redirected to landing from home', async ({ page }) => {
    await page.goto('/');
    
    // Should be redirected to landing page
    await expect(page).toHaveURL(/\/pilot\/landing\//);
  });

  test('unauthenticated user is redirected to landing from account page', async ({ page }) => {
    await page.goto('/pilot/account/');
    
    // Should be redirected to landing page
    await expect(page).toHaveURL(/\/pilot\/landing\//);
  });

  test('unauthenticated user can access login page', async ({ page }) => {
    await page.goto('/pilot/login/');
    
    await expect(page).toHaveURL(/\/pilot\/login\//);
    await expect(page.locator('h1')).toContainText(/Sign in/i);
  });

  test('unauthenticated user can access landing page', async ({ page }) => {
    await page.goto('/pilot/landing/');
    
    await expect(page).toHaveURL(/\/pilot\/landing\//);
  });
});

// ============================================================================
// Registration Flow Tests
// ============================================================================

test.describe('Registration Flow', () => {
  test('complete registration flow with email preference', async ({ page }) => {
    const email = generateTestEmail('signup');
    const phone = generateTestPhone();
    
    await signupWithCampaign(page, VALID_CAMPAIGN_CODE, email, phone, 'email');
    
    // Should be on OTP page
    await expect(page.locator('h1')).toContainText(/Check your phone or email/i);
    await expect(page.locator('body')).toContainText(email);
    
    // In DEBUG mode, OTP should be visible
    const otp = await getDebugOTP(page);
    expect(otp).toBeTruthy();
    expect(otp).toMatch(/^\d{6}$/);
    
    // Verify OTP
    const success = await verifyOTP(page);
    expect(success).toBe(true);
    
    // Should be on home page and authenticated
    await expect(page).toHaveURL('/');
    await expect(page.locator('.nhsuk-header__account')).toBeVisible();
  });

  test('complete registration flow with SMS preference', async ({ page }) => {
    const email = generateTestEmail('sms');
    const phone = generateTestPhone();
    
    await signupWithCampaign(page, VALID_CAMPAIGN_CODE, email, phone, 'sms');
    
    // Should show phone number (partial) on OTP page
    await expect(page.locator('body')).toContainText(/mobile number ending in/i);
    
    // Verify OTP
    const success = await verifyOTP(page);
    expect(success).toBe(true);
  });

  test('registration requires preferred contact method', async ({ page }) => {
    await page.goto(`/pilot/landing/?cc=${VALID_CAMPAIGN_CODE}`);
    await page.locator('#accept').check();
    await page.locator('button[type="submit"]').click();
    
    await page.waitForURL(/\/pilot\/contact-info\//);
    
    // Fill email but don't select preferred method
    await page.locator('#emailInput').fill('test@example.com');
    await page.locator('button[type="submit"]').click();
    
    // Should show error
    await expect(page.locator('.nhsuk-error-summary')).toBeVisible();
  });

  test('registration validates email when email is preferred', async ({ page }) => {
    await page.goto(`/pilot/landing/?cc=${VALID_CAMPAIGN_CODE}`);
    await page.locator('#accept').check();
    await page.locator('button[type="submit"]').click();
    
    await page.waitForURL(/\/pilot\/contact-info\//);
    
    // Select email preference but don't provide email
    await page.locator('#preferredContact').selectOption('email');
    await page.locator('#phoneInput').fill('07987654321');
    await page.locator('button[type="submit"]').click();
    
    // Should show error about email required
    await expect(page.locator('.nhsuk-error-summary')).toBeVisible();
  });

  test('registration validates phone when SMS is preferred', async ({ page }) => {
    await page.goto(`/pilot/landing/?cc=${VALID_CAMPAIGN_CODE}`);
    await page.locator('#accept').check();
    await page.locator('button[type="submit"]').click();
    
    await page.waitForURL(/\/pilot\/contact-info\//);
    
    // Select SMS preference but don't provide phone
    await page.locator('#preferredContact').selectOption('sms');
    await page.locator('#emailInput').fill('test@example.com');
    await page.locator('button[type="submit"]').click();
    
    // Should show error about phone required
    await expect(page.locator('.nhsuk-error-summary')).toBeVisible();
  });

  test('cannot access contact info without accepting disclaimer', async ({ page }) => {
    // Try to go directly to contact info page
    await page.goto('/pilot/contact-info/');
    
    // Should redirect to landing
    await expect(page).toHaveURL(/\/pilot\/landing\//);
  });
});

// ============================================================================
// Login Flow Tests
// ============================================================================

test.describe('Login Flow', () => {
  test('login page shows form', async ({ page }) => {
    await page.goto('/pilot/login/');
    
    await expect(page.locator('h1')).toContainText(/Sign in/i);
    await expect(page.locator('#contact')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('OTP verification with incorrect code shows error', async ({ page }) => {
    // First create a user
    const { email } = await createAuthenticatedUser(page);
    await logout(page);
    
    // Now login
    await login(page, email);
    
    // Enter wrong OTP
    await page.locator('#otp').fill('000000');
    await page.locator('button[type="submit"]').click();
    
    // Should stay on OTP page with error
    await expect(page).toHaveURL(/\/pilot\/otp\//);
    await expect(page.locator('.nhsuk-error-summary')).toBeVisible();
    await expect(page.locator('body')).toContainText(/Invalid or expired/i);
  });

  test('OTP verification shows remaining attempts', async ({ page }) => {
    // First create a user
    const { email } = await createAuthenticatedUser(page);
    await logout(page);
    
    // Now login
    await login(page, email);
    
    // Enter wrong OTP
    await page.locator('#otp').fill('000000');
    await page.locator('button[type="submit"]').click();
    
    // Should show remaining attempts
    await expect(page.locator('body')).toContainText(/attempt\(s\) remaining/i);
  });

  test('successful login with valid OTP', async ({ page }) => {
    // First create a user
    const { email } = await createAuthenticatedUser(page);
    await logout(page);
    
    // Now login
    await login(page, email);
    
    // Verify OTP
    const success = await verifyOTP(page);
    expect(success).toBe(true);
    
    // Should be on home page
    await expect(page).toHaveURL('/');
  });
});

// ============================================================================
// User Enumeration Prevention Tests
// ============================================================================

test.describe('User Enumeration Prevention', () => {
  test('invalid email still shows OTP verify page', async ({ page }) => {
    // Try to login with an email that doesn't exist
    const fakeEmail = `nonexistent_${Date.now()}@example.com`;
    
    await login(page, fakeEmail);
    
    // Should still show OTP page (to prevent enumeration)
    await expect(page).toHaveURL(/\/pilot\/otp\//);
    await expect(page.locator('h1')).toContainText(/Check your phone or email/i);
  });

  test('invalid phone still shows OTP verify page', async ({ page }) => {
    // Try to login with a phone that doesn't exist
    const fakePhone = '07000000000';
    
    await login(page, fakePhone);
    
    // Should still show OTP page (to prevent enumeration)
    await expect(page).toHaveURL(/\/pilot\/otp\//);
    await expect(page.locator('h1')).toContainText(/Check your phone or email/i);
  });

  test('OTP verification fails for non-existent user (same as wrong code)', async ({ page }) => {
    const fakeEmail = `fake_${Date.now()}@example.com`;
    
    await login(page, fakeEmail);
    
    // Try to verify with any code
    await page.locator('#otp').fill('123456');
    await page.locator('button[type="submit"]').click();
    
    // Should show generic error (same as wrong code for real user)
    await expect(page.locator('.nhsuk-error-summary')).toBeVisible();
    await expect(page.locator('body')).toContainText(/Invalid or expired/i);
  });
});

// ============================================================================
// Account Management Tests
// ============================================================================

test.describe('Account Management', () => {
  test.beforeEach(async ({ page }) => {
    await createAuthenticatedUser(page);
  });

  test('account page shows user settings', async ({ page }) => {
    await page.goto('/pilot/account/');
    
    await expect(page.locator('h1')).toContainText(/account/i);
    await expect(page.locator('#id_email')).toBeVisible();
    await expect(page.locator('#id_phone')).toBeVisible();
    await expect(page.locator('#id_postcode')).toBeVisible();
  });

  test('postcode is required', async ({ page }) => {
    await page.goto('/pilot/account/');
    
    // Clear postcode
    await page.locator('#id_postcode').fill('');
    await page.locator('button[type="submit"]').click();
    
    // Should show error
    await expect(page.locator('.nhsuk-error-message')).toBeVisible();
  });

  test('postcode validation', async ({ page }) => {
    await page.goto('/pilot/account/');
    
    // Enter invalid postcode
    await page.locator('#id_postcode').fill('invalid');
    await page.locator('button[type="submit"]').click();
    
    // Should show error
    await expect(page.locator('.nhsuk-error-message')).toBeVisible();
    await expect(page.locator('body')).toContainText(/valid UK postcode/i);
  });

  test('delete account link visible on account page', async ({ page }) => {
    await page.goto('/pilot/account/');
    
    await expect(page.locator('a[href*="delete"]')).toBeVisible();
  });
});

// ============================================================================
// Delete Account Tests
// ============================================================================

test.describe('Delete Account', () => {
  test.beforeEach(async ({ page }) => {
    await createAuthenticatedUser(page);
  });

  test('delete account page shows confirmation', async ({ page }) => {
    await page.goto('/pilot/account/delete/');
    
    await expect(page.locator('h1')).toContainText(/Delete/i);
    await expect(page.locator('body')).toContainText(/cannot be undone/i);
    await expect(page.locator('#id_confirm')).toBeVisible();
  });

  test('delete account requires confirmation checkbox', async ({ page }) => {
    await page.goto('/pilot/account/delete/');
    
    // Try to delete without checking confirmation
    await page.locator('button[type="submit"]').click();
    
    // Should show error
    await expect(page.locator('.nhsuk-error-message')).toBeVisible();
  });

  test('delete account removes user and redirects to landing', async ({ page }) => {
    await page.goto('/pilot/account/delete/');
    
    // Confirm deletion
    await page.locator('#id_confirm').check();
    await page.locator('button[type="submit"]').click();
    
    // Should redirect to landing with success message
    await expect(page).toHaveURL(/\/pilot\/landing\//);
  });

  test('cannot access site after account deletion', async ({ page }) => {
    await page.goto('/pilot/account/delete/');
    
    await page.locator('#id_confirm').check();
    await page.locator('button[type="submit"]').click();
    
    await expect(page).toHaveURL(/\/pilot\/landing\//);
    
    // Try to access home page
    await page.goto('/');
    
    // Should be redirected to landing
    await expect(page).toHaveURL(/\/pilot\/landing\//);
  });
});

// ============================================================================
// Logout and Session Tests
// ============================================================================

test.describe('Logout and Session', () => {
  test.beforeEach(async ({ page }) => {
    await createAuthenticatedUser(page);
  });

  test('logout link visible when authenticated', async ({ page }) => {
    await page.goto('/');
    
    await expect(page.locator('.nhsuk-header__account-link[href="/pilot/logout/"]')).toBeVisible();
  });

  test('logout redirects to landing with message', async ({ page }) => {
    await page.goto('/');
    await logout(page);
    
    await expect(page).toHaveURL(/\/pilot\/landing\//);
  });

  test('cannot access authenticated pages after logout', async ({ page }) => {
    await page.goto('/');
    await logout(page);
    
    // Try to access home page
    await page.goto('/');
    
    // Should redirect to landing
    await expect(page).toHaveURL(/\/pilot\/landing\//);
  });

  test('settings link visible when authenticated', async ({ page }) => {
    await page.goto('/');
    
    await expect(page.locator('.nhsuk-header__account-link[href="/pilot/account/"]')).toBeVisible();
  });
});

// ============================================================================
// Authenticated User Journey Tests
// ============================================================================

test.describe('Authenticated User Journey', () => {
  test.beforeEach(async ({ page }) => {
    await createAuthenticatedUser(page);
  });

  test('authenticated user can access home page', async ({ page }) => {
    await page.goto('/');
    
    await expect(page).toHaveURL('/');
    await expect(page.locator('body')).toContainText(/healthy lifestyle/i);
  });

  test('home page shows correct title', async ({ page }) => {
    await page.goto('/');
    
    await expect(page).toHaveTitle(/NHS - Help to stay healthy/i);
  });
});

// ============================================================================
// Duplicate Registration Prevention Tests
// ============================================================================

test.describe('Duplicate Registration Prevention', () => {
  test('cannot register with existing email', async ({ page }) => {
    const email = generateTestEmail('dupe');
    const phone1 = generateTestPhone();
    const phone2 = generateTestPhone();
    
    // Register first user
    await signupWithCampaign(page, VALID_CAMPAIGN_CODE, email, phone1, 'email');
    await verifyOTP(page);
    await logout(page);
    
    // Try to register with same email
    await page.goto(`/pilot/landing/?cc=${VALID_CAMPAIGN_CODE}`);
    await page.locator('#accept').check();
    await page.locator('button[type="submit"]').click();
    
    await page.waitForURL(/\/pilot\/contact-info\//);
    await page.locator('#emailInput').fill(email);
    await page.locator('#phoneInput').fill(phone2);
    await page.locator('#preferredContact').selectOption('email');
    await page.locator('button[type="submit"]').click();
    
    // Should show error about duplicate email
    await expect(page.locator('.nhsuk-error-summary')).toBeVisible();
    await expect(page.locator('body')).toContainText(/already registered/i);
  });

  test('cannot register with existing phone', async ({ page }) => {
    const email1 = generateTestEmail('dupe1');
    const email2 = generateTestEmail('dupe2');
    const phone = generateTestPhone();
    
    // Register first user
    await signupWithCampaign(page, VALID_CAMPAIGN_CODE, email1, phone, 'sms');
    await verifyOTP(page);
    await logout(page);
    
    // Try to register with same phone
    await page.goto(`/pilot/landing/?cc=${VALID_CAMPAIGN_CODE}`);
    await page.locator('#accept').check();
    await page.locator('button[type="submit"]').click();
    
    await page.waitForURL(/\/pilot\/contact-info\//);
    await page.locator('#emailInput').fill(email2);
    await page.locator('#phoneInput').fill(phone);
    await page.locator('#preferredContact').selectOption('sms');
    await page.locator('button[type="submit"]').click();
    
    // Should show error about duplicate phone
    await expect(page.locator('.nhsuk-error-summary')).toBeVisible();
    await expect(page.locator('body')).toContainText(/already registered/i);
  });
});
