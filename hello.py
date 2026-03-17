"""Hello module providing greeting utilities.

This module contains functions and a class for generating
personalized greeting and farewell messages. It serves as
a demonstration of proper Google-style docstrings.

Example:
    Basic usage::

        >>> greet("World")
        'Hello, World!'
        >>> greeter = Greeter("Alice")
        >>> greeter.greet()
        'Hello, Alice!'
"""


def greet(name: str) -> str:
    """Generate a greeting message for the given name.

    Args:
        name: The name of the person to greet.

    Returns:
        A greeting string in the format "Hello, {name}!".

    Example:
        >>> greet("World")
        'Hello, World!'
    """
    return f"Hello, {name}!"


def farewell(name: str, formal: bool = False) -> str:
    """Generate a farewell message for the given name.

    Args:
        name: The name of the person to bid farewell.
        formal: If True, use a formal farewell. Defaults to False.

    Returns:
        A farewell string, either casual or formal.

    Example:
        >>> farewell("Bob")
        'Goodbye, Bob!'
        >>> farewell("Bob", formal=True)
        'It was a pleasure, Bob. Farewell.'
    """
    if formal:
        return f"It was a pleasure, {name}. Farewell."
    return f"Goodbye, {name}!"


class Greeter:
    """A stateful greeter that remembers a name and tracks interactions.

    Attributes:
        name: The name of the person this greeter is configured for.
        count: The number of greetings issued so far.

    Example:
        >>> g = Greeter("Alice")
        >>> g.greet()
        'Hello, Alice!'
        >>> g.count
        1
    """

    def __init__(self, name: str) -> None:
        """Initialize the Greeter with a name.

        Args:
            name: The name of the person to greet.
        """
        self.name = name
        self.count = 0

    def greet(self) -> str:
        """Generate a greeting and increment the interaction count.

        Returns:
            A greeting string for the configured name.
        """
        self.count += 1
        return greet(self.name)

    def farewell(self, formal: bool = False) -> str:
        """Generate a farewell message using the configured name.

        Args:
            formal: If True, use a formal farewell. Defaults to False.

        Returns:
            A farewell string for the configured name.
        """
        return farewell(self.name, formal=formal)

    def summary(self) -> str:
        """Return a summary of interactions with this greeter.

        Returns:
            A string describing how many greetings were issued.
        """
        return f"Greeted {self.name} {self.count} time(s)."


if __name__ == "__main__":
    greeter = Greeter("World")
    print(greeter.greet())
    print(greeter.farewell())
    print(greeter.summary())
