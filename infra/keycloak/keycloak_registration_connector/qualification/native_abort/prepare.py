#!/usr/bin/env python3
"""Prepare a disposable deny-only native abort experiment. Never install/deploy."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import types


def replace(text,old,new):
    if text.count(old)!=1: raise ValueError("Unexpected exact native patch anchor")
    return text.replace(old,new,1)


def prepare(source,output,mode,qualification_root=None):
    if mode not in {"native","limited","integrated"} or output.resolve().is_relative_to(source.resolve()):
        raise ValueError("Reviewed mode and separate owned output required")
    fixture=Path(__file__).resolve().parent
    shared=qualification_root if qualification_root is not None else fixture.parent
    inputs=json.loads((fixture/"inputs.json").read_text())
    for root,rows in [(source,inputs["native_sources"]),(shared,inputs["reused_files"])]:
        for row in rows:
            p=root/row["path"]
            if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=row["sha256"]:
                raise ValueError("Unreviewed native or prior fixture bytes")
    native={x["path"]:(source/x["path"]).read_text() for x in inputs["native_sources"]}
    # Verify all replacements in memory before creating output.
    manager=native[inputs["native_sources"][0]["path"]]
    session=native[inputs["native_sources"][1]["path"]]
    helper=native[inputs["native_sources"][2]["path"]]
    if mode=="integrated":
        manager=replace(manager,"    private boolean active;", "    private ResearchAbortState researchAbort;\n    private boolean active;")
        extension="""
    public void attachResearchAbort(ResearchAbortState state) {
        state.before((DefaultKeycloakSession)session,"attach.manager");
        if (researchAbort != null) throw new IllegalStateException("Already owned");
        researchAbort=state;
        if(active || completed || !transactions.isEmpty() || !prepare.isEmpty() || !afterCompletion.isEmpty())
            researchAbort.failure("manager.late_attach",new IllegalStateException("Prior lifecycle outcome not owned"));
    }
    public void abortForResearch() {
        if (!researchAbort.startManager()) return;
        boolean previouslyCompleted=completed;
        rollback=true; completed=true; active=false;
        if(previouslyCompleted) {
            researchAbort.failure("manager.completed",new IllegalStateException("Outcome already unknown; never retry"));
            return;
        }
        // Include registration-before-begin failures without resetting native participant state.
        for (KeycloakTransaction tx : researchAbort.registrations()) {
            if ("prepare".equals(researchAbort.role(tx))) continue;
            researchAbort.run("rollback",tx,tx::rollback);
            researchAbort.observe("rollback:"+researchAbort.role(tx));
        }
    }
"""
        manager=replace(manager,"    @Override\n    public void enlist(KeycloakTransaction transaction) {",extension+"\n    @Override\n    public void enlist(KeycloakTransaction transaction) {")
        for method,role in [("enlist","main"),("enlistPrepare","prepare"),("enlistAfterCompletion","after")]:
            anchor="    public void "+method+"(KeycloakTransaction transaction) {"
            manager=replace(manager,anchor,anchor+'\n        if(researchAbort!=null) researchAbort.remember(transaction,"'+role+'");')
        anchor="    public void begin() {"
        manager=replace(manager,anchor,anchor+'\n        if(researchAbort!=null) researchAbort.before((DefaultKeycloakSession)session,"begin");')
        for method in ["commit","rollback"]:
            anchor="    public void "+method+"() {"
            manager=replace(manager,anchor,anchor+"\n        if(researchAbort!=null) { abortForResearch(); throw researchAbort.denied(); }")
        session=replace(session,"    private boolean closed = false;","    private ResearchAbortState researchAbort;\n    private boolean closed = false;")
        extension="""
    public void attachResearchAbort(ResearchAbortState state) {
        state.before(this,"attach.session");
        if(researchAbort!=null) throw new IllegalStateException("Already owned");
        transactionManager.attachResearchAbort(state); researchAbort=state;
    }
    public ResearchAbortState researchAbortState() { return researchAbort; }
    private void closeForResearch() {
        researchAbort.check(this);
        if(!researchAbort.startClose()) throw researchAbort.denied();
        try {
            researchAbort.run("manager.abort",transactionManager,transactionManager::abortForResearch);
            java.util.List<Provider> owned=new java.util.ArrayList<>(providers.values());
            owned.addAll(closable);
            for(Provider p:owned) if(p!=null) researchAbort.run("provider.close",p,p::close);
            for(Entry<InvalidableObjectType,Set<Object>> e:invalidationMap.entrySet()) {
                researchAbort.run("invalidate",e,() -> factory.invalidate(this,e.getKey(),e.getValue().toArray()));
            }
        } finally { closed=true; }
        throw researchAbort.denied();
    }
"""
        session=replace(session,"    @Override\n    public void close() {",extension+"\n    @Override\n    public void close() {\n        if(researchAbort!=null) { closeForResearch(); return; }")
        helper=replace(helper,"            if (session == null || session.isClosed()) {","""            if(session instanceof org.keycloak.services.DefaultKeycloakSession owned && owned.researchAbortState()!=null) {
                owned.close(); return;
            }
            if (session == null || session.isClosed()) {""")
        helper=replace(helper,"            KeycloakSessionUtil.setKeycloakSession(null);","""            if(session instanceof org.keycloak.services.DefaultKeycloakSession owned && owned.researchAbortState()!=null) {
                owned.researchAbortState().clearContext();
            } else { KeycloakSessionUtil.setKeycloakSession(null); }""")
    recipe=shared/"rollback_lifecycle/prepare.py"
    module=types.ModuleType("reviewed_rollback_prepare");module.__file__=str(recipe)
    exec(compile(recipe.read_bytes(),str(recipe),"exec"),module.__dict__)
    module.prepare(source,output,"native" if mode=="native" else "candidate",qualification_root=shared)
    shutil.copyfile(fixture/"pom.xml",output/"pom.xml")
    shutil.copytree(fixture/"src",output/"src",dirs_exist_ok=True)
    for row in inputs["native_sources"][3:]:
        dest=output/"src/main/java"/row["path"].split("/src/main/java/",1)[1]
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/row["path"],dest)
    changed=[]
    if mode=="integrated":
        # This branch retains the limited control's normal/unbound manager semantics.
        manager=manager.replace(module.OLD,module.NEW)
        for row,text in zip(inputs["native_sources"],[manager,session,helper]):
            dest=output/"src/main/java"/row["path"].split("/src/main/java/",1)[1]
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text)
            changed.append(dict(path=row["path"],original_sha256=row["sha256"],overlay_sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
    record=dict(mode=mode,changed_native_sources=changed,unbound_native_or_limited_control_preserved=True,earlier_oracle_comparison_unchanged=True,deny_only=True,complete_cleanup_SQL_JTA_HTTP_or_durable_admission_proved=False)
    (output/"abort-overlay.json").write_text(json.dumps(record,indent=2)+"\n")
    return record


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source",type=Path);parser.add_argument("output",type=Path)
    parser.add_argument("mode",choices=["native","limited","integrated"])
    args=parser.parse_args();print(json.dumps(prepare(args.source,args.output,args.mode),sort_keys=True))
