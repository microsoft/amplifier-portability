"""Bounded owner evidence envelope. Imported observations grant no execution."""
import hashlib
import json
import re

MAX_OWNER_BYTES=8*1024*1024

def canonical_bytes(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')

def envelope(owner,revision,body,*,omissions=None,limit_bytes=MAX_OWNER_BYTES):
    if not isinstance(owner,str) or not re.fullmatch(r'[a-z][a-z0-9.-]{0,99}',owner):raise ValueError('Stable public evidence owner name required')
    if not isinstance(revision,(str,int)) or isinstance(revision,bool):raise ValueError('Opaque evidence revision required')
    if type(limit_bytes) is not int or not 1<=limit_bytes<=MAX_OWNER_BYTES:raise ValueError('Owner evidence exceeds configured bound')
    from .capsule import validate_public
    validate_public(body)
    raw=canonical_bytes(body)
    if len(raw)>limit_bytes:raise ValueError('Owner evidence exceeds bound; return an explicit reviewed partial body with omissions')
    missing=omissions or []
    if not isinstance(missing,list) or len(canonical_bytes(missing))>65536:raise ValueError('Bounded explicit evidence omissions required')
    return {'owner':owner,'version':1,'revision':revision,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'body':body,'omissions':missing,'disposition':'partial' if missing else 'complete','executionAuthority':False}

def verify(value,*,expected_owner=None,limit_bytes=MAX_OWNER_BYTES,accept_partial=False):
    if not isinstance(value,dict) or set(value)!={'owner','version','revision','sha256','bytes','body','omissions','disposition','executionAuthority'}:raise ValueError('Exact owner evidence envelope required')
    if value['version']!=1 or value['executionAuthority'] is not False:raise ValueError('Evidence never transfers execution authority')
    checked=envelope(value['owner'],value['revision'],value['body'],omissions=value['omissions'],limit_bytes=limit_bytes)
    if value!=checked or expected_owner and value['owner']!=expected_owner:raise ValueError('Owner evidence integrity or identity mismatch')
    if value['omissions'] and not accept_partial:raise ValueError('Partial evidence needs explicit preview acceptance')
    return checked
