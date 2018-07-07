if get(s:, 'loaded', 0)
    finish
endif
let s:loaded = 1

let g:ncm2_clang#database_path = get(g:, 'ncm2_clang#database_path', ['compile_commands.json', 'build/compile_commands.json'])
let g:ncm2_clang#clang_command = ['clang']

let g:ncm2_clang#proc = yarp#py3('ncm2_clang_proc')

let g:ncm2_clang#source = get(g:, 'ncm2_clang#source', {
            \ 'name': 'clang',
            \ 'scope': ['cpp', 'c'],
            \ 'priority': 9,
            \ 'mark': 'cxx',
            \ 'on_complete': 'ncm2_clang#on_complete',
            \ 'on_warmup': 'ncm2_clang#on_warmup',
            \ 'complete_pattern': ['-\>', '::', '\.']
            \ })

let g:ncm2_clang#source = extend(g:ncm2_clang#source,
            \ get(g:, 'ncm2_clang#source_override', {}),
            \ 'force')

func! ncm2_clang#init()
    call ncm2#register_source(g:ncm2_clang#source)
endfunc

func! ncm2_clang#on_warmup(ctx)
    call g:ncm2_clang#proc.jobstart()
endfunc

func! ncm2_clang#on_complete(ctx)
    call g:ncm2_clang#proc.try_notify('on_complete',
                \ a:ctx,
                \ getline(1, '$'),
                \ ncm2_clang#_ctx())
endfunc

fun! ncm2_clang#compilation_info()
    py3 << EOF
import vim
import ncm2_clang
from os import path
filepath = vim.eval("expand('%:p')")
filedir = path.dirname(filepath)
ctx = vim.eval("ncm2_clang#_ctx()")
cwd = ctx['cwd']
database_path = ctx['database_path']
args, directory = ncm2_clang.args_from_cmake(filepath, cwd, database_path)
if not args:
    args, directory = ncm2_clang.args_from_clang_complete(filepath, cwd)
ret = dict(args=args or [], directory=directory or cwd)
ret['args'] = ['-I' + filedir] + ret['args']
EOF
    return py3eval('ret')
endf

func! ncm2_clang#_ctx()
    return  {'cwd': getcwd(),
                \ 'database_path': g:ncm2_clang#database_path,
                \ 'clang_command': g:ncm2_clang#clang_command
                \ }
endfunc

