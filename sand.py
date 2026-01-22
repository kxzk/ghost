# /// script
# dependencies = ["modal"]
# ///

from secrets import token_urlsafe

import modal

app = modal.App.lookup(f"ghost-{token_urlsafe(4)}", create_if_missing=True)

# verbose = True (see sandbox logs)
sb = modal.Sandbox.create(app=app, verbose=True)
# sb_id = sb.object_id

# ... later in the program ...

# sb2 = modal.Sandbox.from_id(sb_id)

p = sb.exec("python", "-c", "print('hello')", timeout=3)
print(p.stdout.read())

p = sb.exec("bash", "-c", "for i in {1..10}; do date +%T; sleep 0.5; done", timeout=5)
for line in p.stdout:
    # Avoid double newlines by using end="".
    print(line, end="")

sb.terminate()
