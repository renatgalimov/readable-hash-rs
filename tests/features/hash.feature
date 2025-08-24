Feature: Generate a readable hash
  Scenario: hashing a string
    Given the input "hello"
    When the hash is generated
    Then the result should be "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
