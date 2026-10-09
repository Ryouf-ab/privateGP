import re, difflib
M = {'ا':'a','ب':'b','ت':'t','ث':'th','ج':'j','ح':'h','خ':'kh','د':'d','ذ':'dh','ر':'r','ز':'z','س':'s','ش':'sh','ص':'s','ض':'d','ط':'t','ظ':'d','ع':'','غ':'gh','ف':'f','ق':'q','ك':'k','ل':'l','م':'m','ن':'n','ه':'h','و':'w','ي':'y','ء':'','ئ':'','ؤ':'w',' ':' '}
def ar_skel(s):
    s = re.sub(r'^ال', '', s); s = re.sub(r' ال', ' ', s)
    t = ''.join(M.get(c,'') for c in s)
    return re.sub(r'[aeiouwy\s\-]', '', t)
def en_skel(s):
    s = s.lower(); s = re.sub(r'^(al|an|ar|as|ad|at|ash|az|adh)[- ]', '', s); s = re.sub(r'[ -](al|an|ar|as|ad|at|ash|az)[- ]', ' ', s)
    s = s.replace('ee','i').replace('oo','u').replace('ou','u')
    return re.sub(r'[aeiouwy\s\-\']', '', s)
def sim(a, e): return difflib.SequenceMatcher(None, ar_skel(a), en_skel(e)).ratio()
