@shake256
Feature: Generate English-like words from hash with SHAKE256

  Background:
    Given using the shake256 hasher

  Scenario Outline: hashing strings produces expected output
    Given the input "<input>"
    When the english word hash is generated
    Then the result should be "<output>"

    Examples:
      | input | output        |
      | hello | eying |
      | world | ender |
      | test  | notions |
      |       |                     |
