Zoinks<img width="10%" align="right" src="https://github.com/mhucka/zoinks/raw/main/.graphics/zoinks-icon.png">
======

Zoinks (_**Zo**tero **in**formation quic**k** **s**earch_) is a command-line utility that returns the values of selected fields of a bibliographic record given a Zotero select link, an item key, or even the path to a file attachment in your Zotero database.

[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg?style=flat-square)](https://choosealicense.com/licenses/bsd-3-clause)
[![Latest release](https://img.shields.io/github/v/release/mhucka/zoinks.svg?style=flat-square&color=b44e88)](https://github.com/mhucka/zoinks/releases)


Table of contents
-----------------

* [Introduction](#introduction)
* [Installation](#installation)
* [Usage](#usage)
* [Known issues and limitations](#known-issues-and-limitations)
* [Getting help](#getting-help)
* [Contributing](#contributing)
* [License](#license)
* [Authors and history](#authors-and-history)
* [Acknowledgments](#authors-and-acknowledgments)


Introduction
------------

> "Shaggy has a characteristic speech pattern, marked by his frequent use of the filler word "like" and, when startled, his exclamations of "**Zoinks**!" &mdash; _from the Wikipedia entry for [Shaggy Rogers](https://en.wikipedia.org/wiki/Shaggy_Rogers), retrieved on 2020-12-15. An [archived copy](https://web.archive.org/web/20201112011139/https://en.wikipedia.org/wiki/Shaggy_Rogers) is available in the Wayback Machine._

When using [Zotero](https://zotero.org) in scripts and other software, you may need a way to retrieve information about bibliographic entries without searching for them in Zotero itself.  _Zoinks_ (a loose acronym for _**Zo**tero **in**formation quic**k **s**earch_) is a program that lets you do this from the command line.  Given one or more field names and something that identifies a Zotero record &ndash; an item key, a [Zotero select link](https://forums.zotero.org/discussion/78053/given-the-pdf-file-of-an-article-how-can-you-find-out-its-uri#latest), or just a path to a PDF file in your local Zotero library &ndash; Zoinks returns the values of the fields in the Zotero record.  For example, the following command returns the citation key for a specific paper in my Zotero database:

```sh
zoinks -f citekey zotero://select/library/items/32TR4H94
```

Zoinks is a companion to [Zowie](https://github.com/mhucka/zowie), a command-line application that writes Zotero select links into PDF files to make them accessible outside of Zotero.


Installation
------------

[... forthcoming ...]


Usage
-----

[... forthcoming ...]


Known issues and limitations
----------------------------

[... forthcoming ...]


Getting help
------------

If you find an issue, please submit it in [the GitHub issue tracker](https://github.com/mhucka/zoinks/issues) for this repository.


Contributing
------------

I would be happy to receive your help and participation if you are interested.  Everyone is asked to read and respect the [code of conduct](CONDUCT.md) when participating in this project.  Development generally takes place on the `development` branch.


License
-------

This software is Copyright (C) 2020, by Michael Hucka and the California Institute of Technology (Pasadena, California, USA).  This software is freely distributed under a 3-clause BSD type license.  Please see the [LICENSE](LICENSE) file for more information.


Authors and history
---------------------------

Copyright (c) 2020 by Michael Hucka and the California Institute of Technology.


Acknowledgments
---------------

This work is a personal project developed by the author, using computing facilities and other resources of the [California Institute of Technology Library](https://www.library.caltech.edu).
