import docx, glob

for fpath in sorted(glob.glob('uploads/*.docx')):
    print(f"\n{'='*60}")
    print(f"FILE: {fpath}")
    print('='*60)
    doc = docx.Document(fpath)
    for i, p in enumerate(doc.paragraphs[:60]):
        print(f"[{i:03d}] style={p.style.name!r:20s} text={p.text!r}")
