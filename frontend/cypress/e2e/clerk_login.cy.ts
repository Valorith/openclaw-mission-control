describe("Clerk login (OTP)", () => {
  it("can sign in via Clerk modal", () => {
    // Skip unless explicitly configured.
    const clerkOrigin = Cypress.env("CLERK_ORIGIN");
    const email = Cypress.env("CLERK_TEST_EMAIL");
    const otp = Cypress.env("CLERK_TEST_OTP");

    if (!clerkOrigin || !email || !otp) {
      cy.log("Skipping: missing CYPRESS_CLERK_ORIGIN / CYPRESS_CLERK_TEST_EMAIL / CYPRESS_CLERK_TEST_OTP");
      return;
    }

    cy.visit("/activity");
    cy.loginWithClerkOtp();

    // After login, the SignedIn UI should render.
    cy.contains(/live feed/i, { timeout: 20_000 }).should("be.visible");
  });
});
