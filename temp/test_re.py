import re

t = "yo'qyo'q"
p = re.compile(r"^(yo'q|йўқ)+$", re.IGNORECASE)
print("match", bool(p.match(t)))
