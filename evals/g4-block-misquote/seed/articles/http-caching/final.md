---
title: The Cache-Control header, from max-age to immutable
meta_description: How the cache-control header decides what a browser reuses, with max-age, no-cache, no-store and immutable, and two policies you can copy.
slug: http-caching
---
# The Cache-Control header, from max-age to immutable

The cache-control header tells every cache between your server and the browser how long it may reuse a response and when it
must ask again. By the end of this page you will have two policies you can copy: one for static assets and one for HTML pages.

## What the cache-control header does

Caching rules come from one standard. RFC 9111 defines HTTP caches and the header fields that control what they do [F5]. It
replaced the earlier caching standard, RFC 7234 [F6], so older guides that cite 7234 describe the same ideas under an outdated
name. Every directive below is a field value of this header, and you can send several of them at once, separated by commas.

## max-age: how long a response stays fresh

The directive you will set most often is max-age. The standard puts it this way: "The max-age response directive indicates
that the response is to be considered stale after its age is equal to the specified number of seconds." [F1] While a
response is fresh, a cache can hand it out without asking your server. Once it is stale, the cache has to check with the server
first. Pick the value from how often the content really changes, not from how fast you want the page to feel.

## no-cache vs no-store

These two names sound alike and do opposite jobs. With no-cache, a cache may keep the response, but it must not reuse it for
another request until it has sent it to your server for validation and received a successful answer [F2]. That keeps pages
current while still saving bandwidth when nothing changed. With no-store, a cache must not store any part of the request or the
response at all [F3]. Use no-store for responses that hold private data, and no-cache for pages that change but are safe to keep.

## A fingerprinted asset with immutable

Build tools can put a hash of a file's content into its name, so the name changes whenever the file does. That makes a very
long lifetime safe:

```
Cache-Control: public, max-age=31536000, immutable
```

The immutable directive tells the browser that the response will not be updated while it is fresh [F4], so it skips the
check it would otherwise make on a reload. When you ship a new version, the new file name makes the browser fetch it.

## Your two policies

Give fingerprinted assets a year of max-age plus immutable, and give HTML pages no-cache so readers always get the current
page. To start from a working setup, download the example server config at https://example.com/caching-config.

Signed-off-by:
