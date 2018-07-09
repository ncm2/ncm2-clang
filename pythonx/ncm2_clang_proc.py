# -*- coding: utf-8 -*-

from ncm2 import Ncm2Source, getLogger
import subprocess
import re
from os.path import dirname
from ncm2_clang import args_from_cmake, args_from_clang_complete
import vim
import time

logger = getLogger(__name__)


class Source(Ncm2Source):

    def on_complete(self, ctx, lines, ctx2):

        src = self.get_src("\n".join(lines), ctx).encode('utf-8')
        lnum = ctx['lnum']
        bcol = ctx['bcol']
        filepath = ctx['filepath']
        startccol = ctx['startccol']
        cwd = ctx2['cwd']
        database_path = ctx2['database_path']
        filedir = dirname(filepath)
        clang = ctx2['clang_command']

        scope = ctx['scope']
        if scope == 'cpp':
            lang = 'c++'
        else:
            lang = 'c'

        run_dir = cwd

        clang = [clang] if type(clang) is str else clang
        args = [*clang,
                '-x', lang,
                '-fsyntax-only',
                '-Xclang', '-code-completion-macros',
                # '-Xclang', '-code-completion-brief-comments',
                # Perfer external snippets instead of -code-completion-patterns
                # '-Xclang', '-code-completion-patterns',
                '-Xclang', '-code-completion-at={}:{}:{}'.format(
                    '-', lnum, bcol),
                '-',
                '-I', filedir
                ]

        cmake_args, directory = args_from_cmake(filepath, cwd, database_path)
        if cmake_args is not None:
            args += cmake_args
            run_dir = directory
        else:
            clang_complete_args, directory = args_from_clang_complete(
                filepath, cwd)
            if clang_complete_args:
                args += clang_complete_args
                run_dir = directory

        # args = args + self._clang_opts
        start = time.time()
        logger.debug("args: %s", args)

        proc = subprocess.Popen(args=args,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL,
                                cwd=run_dir)

        result, errs = proc.communicate(src, timeout=30)

        result = result.decode()

        end = time.time()
        logger.debug(
            "code-completion time: %s, result: [%s]", end - start, result)

        matches = []

        for line in result.split("\n"):
            # COMPLETION: cout : [#ostream#]cout
            # COMPLETION: terminate : [#void#]terminate()
            if not line.startswith("COMPLETION: "):
                continue

            try:
                m = self.parse_completion(line)
                matches.append(m)
            except Exception as ex:
                logger.exception("failed parsing completion: %s", line)

        logger.debug("startccol: %s, matches: %s", startccol, matches)

        self.complete(ctx, startccol, matches)

    def parse_completion(self, line):
        m = re.search(r'^COMPLETION:\s+([\w~&=!*/_]+)(\s+:\s+(.*)$)?', line)
        word = m.group(1)

        menu = ''
        snippet = ''
        is_snippet = False
        snippet_num = 0

        if m.group(3):
            # [#double#]copysign(<#double __x#>, <#double __y#>)
            more = m.group(3)
            menu = re.sub(r'\[#([^#]+)#\]', r'\1 ', more)
            menu = menu.replace('<#', '')
            menu = menu.replace('#>', '')
            menu = menu.replace('{#', '[')
            menu = menu.replace('#}', ']')

            if more.find('()') >= 0:
                is_snippet = True

            # function without parameter
            if more.endswith('()'):
                is_snippet = True

            def rep(m):
                nonlocal is_snippet
                nonlocal snippet_num
                is_snippet = True
                snippet_num += 1
                name = m.group(1)
                last_word = re.search('([\w_]+)$', name)
                if last_word:
                    name = last_word.group(1)
                return self.lsp_snippet_placeholder(snippet_num, name)

            snippet = re.sub(r'\[#([^#]+)#\]', r'', more)
            snippet = re.sub(r'\<#([^#]+)#\>', rep, snippet)

            begin = None
            end = None
            mb = re.search('\<#', more)
            me = re.search('.*#\>', more)  # greedy
            if mb:
                begin = mb.start()
            if me:
                end = mb.end()

            opt_begin = None
            opt_end = None
            mob = re.search('\{#', more)
            moe = re.search('.*#\}', more)
            if mob:
                opt_begin = mob.start()
            if moe:
                opt_end = moe.end()

            if opt_begin:
                if opt_begin < begin and opt_end > end:
                    snippet = re.sub(
                        r'\{#.*#\}', self.lsp_snippet_placeholder(1), snippet)
                else:
                    snippet = re.sub(r'\{#.*#\}', '', snippet)

        ud = {}
        ud['is_snippet'] = is_snippet
        ud['snippet'] = snippet
        return dict(word=word, menu=menu, user_data=ud)

    def lsp_snippet_placeholder(self, num, txt=''):
        # https://github.com/Microsoft/language-server-protocol/blob/master/snippetSyntax.md
        if txt == '':
            return '${%s}' % num
        txt = txt.replace('$', r'\$')
        txt = txt.replace('}', r'\}')
        txt = txt.replace('\\', '\\\\')
        return '${%s:%s}' % (num, txt)


source = Source(vim)

on_complete = source.on_complete
