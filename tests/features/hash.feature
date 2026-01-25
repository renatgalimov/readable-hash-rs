Feature: Generate a readable hash

  Background:
    Given using the std hasher

  Scenario: hashing a string produces expected output
    Given the input "hello"
    When the hash is generated
    Then the result should be "elliss niersaftikasus"
