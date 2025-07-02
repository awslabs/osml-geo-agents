# Tox Unit Tests
- Unit tests are executed in the tox environment defined by tox.ini
- Individual unit tests can be run with the following command: tox -e py312 -- test/aws/osml/test_foo.py
- Ignore failures where the required test coverage is not met so long as the tests pass
