@shake256
Feature: Generate a readable hash with SHAKE256

  Background:
    Given using the shake256 hasher

  Scenario: hashing a string produces expected output
    Given the input "hello"
    When the hash is generated
    Then the result should be "old than giviburmaasthem"
