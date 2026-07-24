# Changelog

Version numbers were reassigned for release (the old scheme bumped the
minor version for bugfixes); the original number is in parentheses. The
notes below are from each script's own version history.

Version numbers in the original filenames drifted one ahead of the version history recorded inside them. The changelog is derived from diffing consecutive files rather than from those labels, so it reflects what each file actually contained.

## 1.2.3  (originally 1.6)

UnicodeEncodeError when run through the Manager under a cp1252 console.

## 1.2.2  (originally 1.5)

Blocking HTTP calls killed the Discord gateway heartbeat. They now run in a thread
executor.

## 1.2.1  (originally 1.4)

Two second pause between product lookups to avoid rate limiting.

## 1.2.0  (originally 1.3)

Retry logic, three attempts with a three second delay. Per-request timeout raised
from 15s to 20s.

## 1.1.0  (originally 1.2)

Playwright replaced with direct calls to the homedepot.ca product API. No browser,
no auth, and the dependency is gone.

## 1.0.1  (originally 1.1)

Intercepted the page's own XHR to recover aisle and bay data, and set the store
cookie so the correct store loads.

## 1.0.0  (originally 1.0)

First version. Scraped product pages with Playwright.

