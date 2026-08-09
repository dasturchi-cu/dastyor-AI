import re
import zipfile

z = zipfile.ZipFile("temp/ref_converted.docx")
xml = z.read("word/document.xml").decode("utf-8")
print("w:u tags", len(re.findall(r"<w:u ", xml)))
print("proofErr", len(re.findall(r"w:proofErr", xml)))
print("highlight", len(re.findall(r"w:highlight", xml)))
print("w:shd", len(re.findall(r"w:shd", xml)))

# value row indents in XML - search for ind with 4320 twips etc
inds = re.findall(r"<w:ind[^>]*/>", xml)
print("ind tags", len(inds))
for x in inds[:15]:
    print(" ", x)
