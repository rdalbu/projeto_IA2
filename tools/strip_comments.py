
"""
Strip non‑essential comments from the project tree.

Safe by default:
 - Python: removes # comments via tokenize; preserves code and strings (docstrings untouched).
 - JS/TS: removes // line comments and /* */ block comments (best‑effort, skips inside quotes heuristically disabled by default).
 - CSS: removes /* */ block comments.
 - HTML: removes <!-- --> comments.

Usage examples:
  python tools/strip_comments.py --dry-run                # show planned changes
  python tools/strip_comments.py --write                  # apply changes
  python tools/strip_comments.py --write --extensions .py .js .css .html
  python tools/strip_comments.py --write --exclude esp32_sketch models

Notes:
 - Creates a .bak next to each modified file unless --no-backup.
 - JS/CSS/HTML stripping is regex-based and best‑effort; review diffs.
 - Use --aggressive to also strip Python docstrings and JSDoc blocks (riskier).
"""

from__future__importannotations
importargparse
importio
importos
importre
importsys
importtokenize
fromtypingimportIterable


DEF_EXTS=[".py",".js",".mjs",".cjs",".ts",".css",".html",".htm"]


defis_binary(path:str,chunk_size:int=8000)->bool:
    try:
        withopen(path,"rb")asf:
            b=f.read(chunk_size)
ifb"\0"inb:
            returnTrue
exceptException:
        returnTrue
returnFalse


defstrip_python(src:str,aggressive:bool=False)->str:
    out=io.StringIO()
prev_toktype=None
first_stmt_seen=False
try:
        tokens=tokenize.generate_tokens(io.StringIO(src).readline)
fortok_type,tok_str,start,end,lineintokens:
            iftok_type==tokenize.COMMENT:
                continue
ifaggressiveandtok_type==tokenize.STRINGandnotfirst_stmt_seen:

                continue
out.write(tok_str)

iftok_typenotin{tokenize.NL,tokenize.NEWLINE,tokenize.INDENT,tokenize.DEDENT,
tokenize.ENCODING}andnot(tok_type==tokenize.STRINGandnotfirst_stmt_seen):
                first_stmt_seen=True
prev_toktype=tok_type
returnout.getvalue()
exceptException:
        returnsrc


_re_js_line=re.compile(r"(^|[\n\r])\s*//.*?(?=$|[\r\n])",re.DOTALL)
_re_block=re.compile(r"/\*.*?\*/",re.DOTALL)
_re_html=re.compile(r"<!--.*?-->",re.DOTALL)


defstrip_text_generic(src:str,ext:str,aggressive:bool=False)->str:
    out=src
ifextin(".js",".mjs",".cjs",".ts"):

        out=_re_block.sub("",out)
out=_re_js_line.sub(lambdam:m.group(1),out)
elifext==".css":
        out=_re_block.sub("",out)
elifextin(".html",".htm"):
        out=_re_html.sub("",out)
returnout


defiter_files(root:str,exts:Iterable[str],exclude:Iterable[str])->Iterable[str]:
    exts=tuple(exts)
exclude_set=set(os.path.normpath(p)forpinexclude)
fordirpath,dirnames,filenamesinos.walk(root):

        norm=os.path.normpath(dirpath)
ifany(norm.startswith(e+os.sep)ornorm==eforeinexclude_set):
            continue
fornameinfilenames:
            ext=os.path.splitext(name)[1].lower()
ifextinexts:
                yieldos.path.join(dirpath,name)


defmain():
    ap=argparse.ArgumentParser()
ap.add_argument("--write",action="store_true",help="apply changes to files")
ap.add_argument("--dry-run",action="store_true",help="show planned changes (default)")
ap.add_argument("--extensions",nargs="*",default=DEF_EXTS,help="file extensions to process")
ap.add_argument("--exclude",nargs="*",default=[".venv","models","node_modules","dist","build"],help="paths to exclude")
ap.add_argument("--aggressive",action="store_true",help="strip more aggressively (e.g., Python docstrings)")
ap.add_argument("--no-backup",action="store_true",help="do not create .bak files when writing")
args=ap.parse_args()

ifnotargs.write:
        args.dry_run=True

changed=0
forpathiniter_files(os.getcwd(),args.extensions,args.exclude):
        try:
            ifis_binary(path):
                continue
withopen(path,"r",encoding="utf-8",errors="ignore")asf:
                src=f.read()
ext=os.path.splitext(path)[1].lower()
ifext==".py":
                dst=strip_python(src,aggressive=args.aggressive)
else:
                dst=strip_text_generic(src,ext,aggressive=args.aggressive)
ifdst!=src:
                changed+=1
ifargs.dry_run:
                    rel=os.path.relpath(path)
print(f"would change: {rel}")
else:
                    ifnotargs.no_backup:
                        withopen(path+".bak","w",encoding="utf-8")asb:
                            b.write(src)
withopen(path,"w",encoding="utf-8")asw:
                        w.write(dst)
exceptExceptionase:
            print(f"skip {path}: {e}")

ifargs.dry_run:
        print(f"Dry run complete. Files to change: {changed}")
else:
        print(f"Done. Files changed: {changed}")


if__name__=="__main__":
    main()

