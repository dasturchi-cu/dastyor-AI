from features.obyektivka.malumotnoma_data import build_malumotnoma_data, _resolve_current_display, _canonical_work_item, _parse_work_list

raw = {
    "lang": "uz_lat",
    "work_experience": [{"f": "2011", "t": "h.v", "fs": "5oktabr", "d": ""}],
}
items = [_canonical_work_item(w) for w in _parse_work_list(raw)]
print("items", items)
job, year = _resolve_current_display(items, lang="uz_lat")
print("resolved", job, year)
print("mdata", build_malumotnoma_data(raw))
