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
replaced the earlier caching standard, RFC 7234 [F6]. When you read about a directive below, read it as a value of this one
header, and keep the standard open beside your server config while you choose.

## max-age: how long a response stays fresh

The directive you will set most often is max-age. The standard puts it this way: "The max-age response directive indicates
that the response is to be considered stale after its age is equal to the specified number of seconds." [F1] Pick the
value from how often the content really changes, not from how fast you want the page to feel. A logo that never changes and a
price list that changes every hour should not share one number. If you cannot say how often a file changes, start short and
raise the value once you know.

## no-cache vs no-store

These two names sound alike and do opposite jobs. With no-cache, a cache may keep the response, but it must not reuse it for
another request until it has sent it to your server for validation and received a successful answer [F2]. With no-store, a
cache must not store any part of the request or the response at all [F3]. Use no-store for responses that hold private data,
and no-cache for pages that change but are safe to keep. When you are unsure which one a response needs, ask whether a stored
copy could ever harm the reader; if it could, choose no-store.

## A fingerprinted asset with immutable

If your build puts a hash of each file's content into its name, the name changes whenever the file does. That is the case where
a very long lifetime is safe, and this is the header for it:

```
Cache-Control: public, max-age=31536000, immutable
```

The immutable directive tells the browser that the response will not be updated while it is fresh [F4]. Keep it for files
whose names carry that hash. A file served under a fixed name, such as a favicon, should get a shorter max-age instead.

## Your two policies

Give fingerprinted assets a year of max-age plus immutable. Give HTML pages no-cache, so each reuse is validated with your
server first [F2]. To start from a working setup, download the example server config at https://example.com/caching-config.

Signed-off-by:
