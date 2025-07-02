
# Coding Style Conventions
- Use type hints for all function signatures.
- Use the python logging framework and get a new logger for each module using `logging.getLogger(__name__)`.
- Comments in code should focus on why a piece of software was written; include info from prompts as necessary.

# Unit Tests
- Use the Python unittest framework and organize tests using classes that extend TestCase.
- Use the Moto library to provide mock AWS services for unit tests.
- Do not mock dataclasses or simple structures.
- Do not mock numpy classes/functions; unit tests should ensure those libraries execute correctly.

# API Documentation
- Use the Sphinx docstring format with :param: :raises: and :return: directives.
- Do not include :type: and :rtype: directives because sphinx-autodoc-typehints will automatically document types from annotations.
