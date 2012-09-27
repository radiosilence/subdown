=======
subdown
=======

Simple tool to download image from subreddit(s).

:Authors:
    James Cleveland

:Version: 0.2


Installation
============

::

    pip install subdown


Also available in the AUR_ (for Arch Linux users)

.. _AUR: https://aur.archlinux.org/packages.php?ID=63180


Usage
-----

::

    % subdown
    Usage:
        subdown [options] <subreddit> [<subreddit>...]
        subdown -h | --help
        subdown --version

    Options:
        -h --help                   Show this screen.
        --version                   Show version.
        -p --pages=COUNT            Number of pages to grab [default: 1].
        -t --timeout=SECONDS        Timeout for individual images [default: 5].
        -T --page-timeout=SECONDS   Timeout for subreddit pages [default: 20].
