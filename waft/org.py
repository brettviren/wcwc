#! /usr/bin/env waf
'''A waf tool to perform org export.

By default it will execute an new instance of emacs for each export.
This can be slow and the emacs may lack the desired configuration.  An
alternative that address both of these is to use emacs daemon through
emacsclient.

  waf configure --emacs-daemon="NAME" [...]

Where NAME is the daemon naem.  Eg when started as:

  emacs --daemon=myemacs

The --emacs-daemon="NAME" may also be given at build time:

  waf --emacs-daemon="NAME" --target=my-export-html

You may also run (server-start) inside a running emacs.  If so, the
name should be "server".  Take caution, a large build may make the
running emacs effectively unusable.

'''

import time
from waflib.Utils import to_list, subst_vars
from waflib.Task import Task, TaskSemaphore
from waflib.Logs import debug, info, error, warn
from waflib import TaskGen

class org_export(Task):

    before = ['inst']

    export_file_name = None

    # Emacs will only write to a fixed file name, which then this task
    # may move to the target.  But, two tasks making a file (of the
    # same extension) will collide.  
    semaphore = TaskSemaphore(1)

    def __init__(self, *k, **kw):
        Task.__init__(self, *k, **kw)
        self.org_linked_files_done = False

    def scan(self):

        node = self.inputs[0]
        deps = set()
        debug(f'org: SCANNING {node}')
        file_links = set()
        for line in node.read().split("\n"):

            efn = "#+export_file_name:"
            if line.lower().startswith(efn):
                self.export_file_name = line.split(":",1)[1].strip()
                debug("org: scan found " + self.export_file_name)
                continue

            pre = "#+include:"
            if line.lower().startswith(pre):
                fname = line[len(pre):].strip()
                fname = fname.split(" ")[0]
                dep = node.parent.find_resource(fname)
                if dep:
                    debug(f"org: scan of {node} dependency found: {fname}")
                    deps.add(dep)
                else:
                    debug(f"org: scan of {node} dependency not found: {fname}")                    

            for word in line.split(' '):
                if word.startswith ("[["):
                    word = word[2:].split("]")[0]
                    chunks = word.split(":")
                    # debug(f'org: PARSED chunks={chunks}')
                    if len(chunks) < 1:
                        continue
                    if chunks[0] != "file":
                        continue
                    flink = chunks[1]
                    if flink.endswith(".org"):
                        continue
                    file_links.add(flink)

        # file_links available in raw_deps
        return (list(deps),list(file_links))

    def runnable_status(self):
        'Install any linked files'
        ret = super(org_export, self).runnable_status() 
        if self.org_linked_files_done:
            return ret

        bld = self.generator.bld
        flinks = bld.raw_deps.get(self.uid(), [])
        # debug(f'org: BLD: {type(bld)} {bld}')
        top_dir = bld.root.find_dir(bld.top_dir)
        node = self.inputs[0]
        outnode = self.outputs[0]
        fnodes = []
        debug(f'org: SCAN: {node} -> {outnode}')
        for flink in flinks:
            if not flink.strip():
                continue
            if node.parent.find_dir(flink):
                debug(f'org: SCAN: ignoring linked directory {flink}')
                continue
            fnode = node.parent.find_resource(flink)
            if not fnode:
                warn(f'org: SCAN: failed to find {flink} needed by {fnode}')
                continue
            debug(f'org: SCAN: found link: {flink} as {fnode}')
            fnodes.append(fnode)
        if fnodes:
            debug(f'org: SCAN: {node} installing ({len(fnodes)}) to {bld.env.DOCS_PREFIX} relative to {top_dir}: {fnodes}')
            bld.install_files(bld.env.DOCS_PREFIX, fnodes,
                              cwd=top_dir, relative_trick=True, postpone=False)
        self.org_linked_files_done = True
        return ret

    def run(self):
        onode = self.inputs[0]
        enode = self.outputs[0]

        dotext = '.' + self.func.split("-")[-1]

        efn = self.export_file_name
        if efn:
            if not efn.endswith(dotext):
                efn += dotext
            tmp = onode.parent.make_node(efn)
        else:
            tmp = onode.parent.make_node(onode.name.replace('.org', dotext))

        debug(f"org: emacs will produce: {tmp}")

        if 'EMACSCLIENT' in self.env and self.env.EMACS_DAEMON:
            cmd = """${EMACSCLIENT} -s "${EMACS_DAEMON}" -e '(progn (find-file "%s") (%s))' > /dev/null 2>&1""" % \
                (onode.abspath(), self.func)
        else:
            cmd = "${EMACS} %s --batch -f %s" % (onode.abspath(), self.func)
        if tmp != enode:
            debug(f"org: will move {tmp} to {enode}")
            move = "mv %s %s" % (tmp, enode.abspath())
            cmd += " && " + move
        cmd = subst_vars(cmd, self.env)
        debug(f'org: COMMAND: {cmd}')
        return self.exec_command(cmd, shell=True)
    

class org_export_html(org_export):
    func = "org-html-export-to-html"

class org_export_pdf(org_export):
    func = "org-latex-export-to-pdf"


@TaskGen.feature("org2html", "org2pdf")
@TaskGen.before('process_source')
def transform_source(tgen):
    tgen.inputs = tgen.to_nodes(getattr(tgen, 'source', []))


@TaskGen.extension('.org')
def process_org(tgen, node):
    
    tgt = getattr(tgen, 'target', [])
    if isinstance(tgt, str):
        tgt = tgen.bld.path.find_or_declare(tgt)
    tgt = tgen.to_nodes(tgt)

    if 'org2html' in tgen.features:
        tgt = tgt or node.change_ext(".html")
        tgen.create_task("org_export_html", node,tgt)

    if 'org2pdf' in tgen.features:
        tgt = tgt or node.change_ext(".pdf")
        tgen.create_task("org_export_pdf", node, tgt)

def options(opt):
    opt.add_option("--emacs-daemon", default=None, type=str,
                   help="Given name of emacs daemon to use via emacsclient for org export.  If none, use emacs directly (which is slower and may not pick up your config) [default=None], Note default daemon is called 'server'")
    opt.add_option("--docs-prefix", default=None, type=str,
                   help="Location for documentation to be installed")
    opt.add_option("--docs-formats", default=None, type=str,
                   help="List of formats for produced documentation (comma separated list)")
    
def configure(cfg):
    cfg.find_program("emacs", var="EMACS", mandatory=False)
    cfg.find_program("emacsclient", var="EMACSCLIENT", mandatory=False)

    cfg.env.EMACS_DAEMON = cfg.options.emacs_daemon

    cfg.env.DOCS_FORMATS = (cfg.options.docs_formats or "").split(",")
    cfg.env.DOCS_PREFIX = cfg.options.docs_prefix
    
def build_org_docs(bld, orgs=()):
    bld_dir = bld.root.find_dir(bld.out_dir)

    for org in orgs:
        for ext in ('html', 'pdf'):
            feat = 'org2'+ext

            out = org.parent.find_or_declare(org.name.replace(".org","."+ext))
            bld(name=org.parent.name + '-' + out.name.replace(".","-"),
                features=feat, source=org, target=out)
            if ext == 'html':
                bld.install_files(dest=bld.env.DOCS_PREFIX, files=out,
                                  cwd=bld_dir, relative_trick=True)

    

def build(bld):
    emacsd = getattr(bld.options, 'emacs_daemon')
    if emacsd is not None:
        bld.env.EMACS_DAEMON = emacsd
    bld.build_org_docs = build_org_docs.__get__(bld, bld.__class__)
