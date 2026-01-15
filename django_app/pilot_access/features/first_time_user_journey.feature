Feature: First-time user journey with campaign code
  As a new user
  I want to join the pilot program using a valid campaign code
  So that I can access the weight management service

  Background:
    Given I have a valid campaign code

  Scenario: First-time user visits landing page with valid campaign code
    When I visit the landing page with the campaign code
    Then I should see the landing page
    And I should see the campaign disclaimer
    And I should see the campaign description

  Scenario: First-time user journey - from landing to contact info
    When I visit the landing page with the campaign code
    And I accept the disclaimer
    Then I should be redirected to the contact information page
    And the session should contain the campaign code
    And the session should have disclaimer accepted flag set

  Scenario: First-time user sees invalid campaign code message
    When I visit the landing page with an invalid campaign code
    Then I should see an error message about invalid campaign code
    And I should not see the campaign disclaimer

  Scenario: First-time user sees expired campaign code message
    Given I have an expired campaign code
    When I visit the landing page with the expired campaign code
    Then I should see an error message about invalid campaign code
    And I should not see the campaign disclaimer

  Scenario: First-time user can access landing without campaign code
    When I visit the landing page without a campaign code
    Then I should see the landing page
    And I should see the magic link login option
