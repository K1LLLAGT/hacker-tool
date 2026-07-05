"""
crypto/keygen.py — CSPRNG secrets, tokens, UUIDs, passphrases, API keys.

Uses the `secrets` module (cryptographically secure), never `random`.

    python modules/crypto/keygen.py hex --bytes 32
    python modules/crypto/keygen.py token
    python modules/crypto/keygen.py uuid
    python modules/crypto/keygen.py passphrase --words 6
    python modules/crypto/keygen.py apikey --prefix ht
    python modules/crypto/keygen.py password --length 20
"""
from __future__ import annotations

import argparse
import math
import secrets
import string
import sys
import uuid

# Compact built-in wordlist for passphrases (entropy/word = log2(len)).
WORDS = (
    "able acid aged also apex arc arch army atom aunt aura axis bake bald band "
    "bank bare bark barn base bash bead beam bean bear beat beef bell belt bend "
    "best bike bind bird bite blue boat body bold bolt bond bone book boot bore "
    "born boss both bulk bull bump bush bust busy cafe cage cake calm camp cane "
    "card care cargo cart case cash cave cell chef chin chip city clan claw clay "
    "clip club coal coat code coin cold cook cool copy cord core corn cost cove "
    "crab crew crop crow curl dark dash data dawn deal dean deck deep deer desk "
    "dial dice dirt dish dive dock dome door dose dove drag draw drip drum dual "
    "duck dune dusk dust duty each earl earn ease east easy echo edge epic even "
    "face fact fade fair fall fame farm fast fate fawn fear feat feed fern file "
    "film find fine fire fish fist five flag flap flat flaw flax flip flow foam "
    "foil fold folk font food fool foot fork form fort four fowl free frog fuel "
    "fund fury fuse gain gala game gate gaze gear gem gift gild girl glad glow "
    "goal goat gold golf gone good gray grid grim grin grip grow gulf hail hair "
    "half hall hand hang harm hawk haze head heal heap heat herb herd hero hide "
    "high hill hint hive hold hole holy home hood hook hope horn host hour huge "
    "hull hunt hymn icon idea idle inch iris iron isle item jade jail jazz jean "
    "jest joke jolt jump junk jury just keel keen kelp kept kern kick kiln "
    "kind king kiss kite knee knot lace lake lamp land lane lark lava lawn lead "
    "leaf lean leap left lens lily lime line link lion list load loaf loam lock "
    "loft logo lone long look loom loop lord lore loud love luck lump lung lure "
    "lush lyre made maid mail main mane many maple mark mars mash mask mast mate "
    "math maze meal mean meat mesh mild mile milk mill mind mine mint mist moat "
    "mode mole monk mood moon moss most moth move mule muse nail name navy near "
    "neat neck nest node noon norm nose note noun oak oath oats onyx opal open "
    "oral orbit ore oval oven owl page pale palm park part pass past path pave "
    "peak pear peat peel pier pike pile pine pink pint pipe plan play plot plow "
    "plum plus poem poet pole pond pony pool pope pork port pose posh post pray "
    "prey prim prop pull pulp pump pure push quad quay quiz race rack raft rail "
    "rain rake ramp rank rare rash rate rave read reap reef reel rely rent "
    "rest rice rich ride rift ring rink riot rise risk roam road roar robe rock "
    "role roof rook room root rope rose ruby ruin rule rune runt rush rust"
).split()
# Deduplicate (order-preserving) so entropy = log2(len(WORDS)) is exact.
WORDS = list(dict.fromkeys(WORDS))


def gen(kind: str, **kw) -> str:
    if kind == "hex":
        return secrets.token_hex(kw.get("nbytes", 16))
    if kind == "token":
        return secrets.token_urlsafe(kw.get("nbytes", 24))
    if kind == "uuid":
        return str(uuid.uuid4())
    if kind == "passphrase":
        n = kw.get("words", 6)
        sep = kw.get("sep", "-")
        return sep.join(secrets.choice(WORDS) for _ in range(n))
    if kind == "apikey":
        prefix = kw.get("prefix", "ht")
        return f"{prefix}_{secrets.token_urlsafe(kw.get('nbytes', 24))}"
    if kind == "password":
        length = kw.get("length", 20)
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_=+"
        while True:
            pw = "".join(secrets.choice(alphabet) for _ in range(length))
            if (any(c.islower() for c in pw) and any(c.isupper() for c in pw)
                    and any(c.isdigit() for c in pw)):
                return pw
    raise ValueError(kind)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="crypto keygen", description="Generate secrets.")
    ap.add_argument("kind", choices=["hex", "token", "uuid", "passphrase", "apikey", "password"])
    ap.add_argument("--bytes", type=int, default=None, dest="nbytes")
    ap.add_argument("--words", type=int, default=6)
    ap.add_argument("--length", type=int, default=20)
    ap.add_argument("--prefix", default="ht")
    ap.add_argument("--sep", default="-")
    ap.add_argument("-n", type=int, default=1, help="how many to generate")
    args = ap.parse_args(argv)

    kw = {"words": args.words, "length": args.length, "prefix": args.prefix,
          "sep": args.sep}
    if args.nbytes is not None:
        kw["nbytes"] = args.nbytes
    for _ in range(args.n):
        print(gen(args.kind, **kw))

    if args.kind == "passphrase":
        bits = args.words * math.log2(len(WORDS))
        print(f"; ~{bits:.0f} bits entropy ({len(WORDS)}-word list)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
