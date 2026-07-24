import re

def _parse_version(version_str: str) -> list:
    parts = []
    for part in re.split(r'(\d+|\D+)', version_str):
        if part:
            try:
                parts.append(int(part))
            except ValueError:
                parts.append(part)
    return parts

def _compare_parts(a, b):
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            return -1 if a[i] < b[i] else 1
    return -1 if len(a) < len(b) else (1 if len(a) > len(b) else 0)

def compare_evr(epoch1, ver1, rel1, epoch2, ver2, rel2):
    e1 = int(epoch1) if epoch1 is not None else 0
    e2 = int(epoch2) if epoch2 is not None else 0
    if e1 != e2:
        return -1 if e1 < e2 else 1
    
    v1 = _parse_version(ver1)
    v2 = _parse_version(ver2)
    result = _compare_parts(v1, v2)
    if result != 0:
        return result
    
    r1 = _parse_version(rel1)
    r2 = _parse_version(rel2)
    return _compare_parts(r1, r2)