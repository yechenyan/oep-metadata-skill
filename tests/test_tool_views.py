"""Observable contracts for compact tools, candidate inputs and clean review packets."""
import copy
import json
from pathlib import Path

import pytest

import oep_metadata
from oepmeta import workflows as w
from oepmeta.common import WorkflowError, json_hash, load_json, write_json
from oepmeta.validate import build_skeleton, validate_metadata
from oepmeta.profile import profile_data


@pytest.fixture
def run(tmp_path):
    data=tmp_path/'data.csv'
    data.write_text('year,power\n2035,1.2\n2040,2.3\n')
    source=tmp_path/'source.md'
    source.write_text('Title: Capacity scenarios. Installed capacity in MW by scenario year. Licensing is undeclared.')
    out=tmp_path/'run'
    w.collect('generate-review',out,data=data,background=[source])
    return out


def candidate(out):
    context=w.inspect(out)['context']
    metadata=copy.deepcopy(context['metadata'])
    metadata['resources'][0]['title']='Capacity scenarios'
    eid=next(e['id'] for e in context['evidence'] if e['kind']=='background')
    return {'input_hash':context['input_hash'],'metadata':metadata,'provenance':[
        {'pointer':'/resources/0/title','status':'supported','evidence_ids':[eid],'rationale':'Documented title.'}]}


def test_generation_view_reuses_context_without_repeated_profile_or_review_data(run):
    before=(run/'.work/context.json').read_bytes()
    full=w.inspect(run)
    view=w.inspect(run,view='generation')
    assert view['context']['input_hash']==full['context']['input_hash']
    assert view['context']['metadata']==full['context']['metadata']
    assert view['context']['profile']==full['context']['profile']
    assert 'review_fields' not in view['context'] and 'provenance' not in view['context']
    profile=next(e for e in view['context']['evidence'] if e['kind']=='data_profile')
    assert 'content' not in profile and profile['content_ref']=='/context/profile'
    assert profile['id']==next(e['id'] for e in full['context']['evidence'] if e['kind']=='data_profile')
    assert len(json.dumps(view))<len(json.dumps(full))
    assert (run/'.work/context.json').read_bytes()==before
    assert w.record_metadata(run,candidate(run))['ok']


def test_export_excludes_generation_rationale_and_previous_review(run):
    value=candidate(run)
    value['provenance'][0]['rationale']='Private generation reasoning should not reach the Reviewer.'
    w.record_metadata(run,value)
    context=w.inspect(run)['context']
    opinion={'input_hash':context['input_hash'],'metadata_hash':context['metadata_hash'],'summary':'Prior reviewer answer.',
             'entries':[{'pointer':f['pointer'],'decision':'unknown','comment':'Earlier opinion must not reach a fresh Reviewer.','evidence_ids':[]} for f in context['review_fields']]}
    w.record_review(run,opinion,independent=True)
    manifest=w.reviewer_input(run)
    packet=load_json(run/manifest['packet_from_run'])
    serialized=json.dumps(packet)
    assert 'Private generation reasoning' not in serialized
    assert 'Earlier opinion' not in serialized and 'Prior reviewer answer' not in serialized
    assert 'provenance' not in packet['context'] and 'review' not in packet
    assert packet['context']['metadata_hash']==context['metadata_hash']
    assert [f['pointer'] for f in packet['context']['review_fields']]==[f['pointer'] for f in context['review_fields']]
    assert manifest['packet_hash']==json_hash({k:v for k,v in packet.items() if k!='packet_hash'})
    assert 'role_instructions' in packet
    assert len(packet['program_verified_pointers'])==manifest['program_verified_count']
    assert packet['source_integrity']['snapshot_hashes_verified_by_tool'] is True
    extra=run.parent/'extra.md';extra.write_text('Supplementary declaration.')
    w.add_evidence(run,extra,kind='declaration')
    new=w.reviewer_input(run)
    assert new['input_hash']!=manifest['input_hash'] and new['packet_hash']!=manifest['packet_hash']
    with pytest.raises(WorkflowError,match='input_hash'):
        w.record_review(run,opinion,independent=True)


@pytest.mark.parametrize('option',['--metadata','--candidate'])
def test_check_accepts_candidate_without_creating_bare_copy(run,tmp_path,capsys,option):
    value=candidate(run);path=tmp_path/'candidate.json';write_json(path,value)
    before=(run/'.work/context.json').read_bytes()
    assert oep_metadata.main(['check',option,str(path),'--run',str(run)])==0
    result=json.loads(capsys.readouterr().out)
    assert result['input_kind']=='candidate' and result['checks']['mechanical_valid']
    assert (run/'.work/context.json').read_bytes()==before
    value['metadata']['resources'][0]['publicationDate']='2040-99-99';write_json(path,value)
    assert oep_metadata.main(['check',option,str(path),'--run',str(run)])==1
    assert not json.loads(capsys.readouterr().out)['checks']['mechanical_valid']


def test_profile_response_can_feed_template_and_check(tmp_path,capsys):
    data=tmp_path/'data.csv';data.write_text('value\n1\n2\n')
    assert oep_metadata.main(['profile','--data',str(data)])==0
    response=json.loads(capsys.readouterr().out)
    envelope=tmp_path/'profile.json';write_json(envelope,response)
    assert oep_metadata.main(['template','--profile',str(envelope)])==0
    template=json.loads(capsys.readouterr().out)['metadata']
    assert [f['name'] for f in template['resources'][0]['schema']['fields']]==['value']
    template['resources'][0]['schema']['fields'][0]['nullable']=False
    profile=response['profile'];profile['columns']['value']['null_count']=1
    assert not validate_metadata(template,profile={'ok':True,'profile':profile})['mechanical_valid']
    assert len(build_skeleton(response)['resources'][0]['schema']['fields'])==1


@pytest.mark.parametrize('value',[{}, {'ok':True}, {'profile':{}}, {'columns':[]}, {'columns':{'value':{}}}])
def test_invalid_profile_does_not_silently_produce_zero_fields(value):
    with pytest.raises(WorkflowError,match='[Pp]rofile'):
        build_skeleton(value)


def test_cli_default_is_compact_and_diagnostics_preserve_exit_codes(run,tmp_path,capsys):
    assert oep_metadata.main(['inspect','--out',str(run)])==0
    output=capsys.readouterr().out
    assert len(output.splitlines())==1 and json.loads(output)['view']=='generation'
    assert oep_metadata.main(['--pretty','inspect','--out',str(run),'--view','full'])==0
    assert len(capsys.readouterr().out.splitlines())>1
    wrong=tmp_path/'wrong.json';write_json(wrong,{'input_hash':'stale','metadata':{}})
    assert oep_metadata.main(['record-metadata','--out',str(run),'--candidate',str(wrong)])==2
    assert 'input_hash' in json.loads(capsys.readouterr().err)['error']
    events=[json.loads(line) for line in (run/'.work/tool-events.jsonl').read_text().splitlines()]
    assert [e['exit_code'] for e in events]==[0,0,2]
    assert all(e['dispatch_elapsed_ms']>=0 and e['response_bytes']>0 for e in events)
    assert str(tmp_path) not in (run/'.work/tool-events.jsonl').read_text()
    assert not list(run.rglob('validation.json')) and not list(run.rglob('questions.json'))


def test_packet_is_self_contained_and_record_counts_cannot_be_spoofed(run):
    w.record_metadata(run,candidate(run))
    manifest=w.reviewer_input(run)
    packet=load_json(run/manifest['packet_from_run'])
    value=packet['candidate_template']
    assert value['input_hash']==packet['context']['input_hash']
    assert value['metadata_hash']==json_hash(packet['context']['metadata'])
    assert set(packet['entry_contract']['decisions'])==w.DECISIONS
    value['entries']=[{'pointer':f['pointer'],'decision':'unknown','comment':'Evidence is insufficient for this fixture.',
                       'evidence_ids':[], 'origin':'program'} for f in packet['context']['review_fields']]
    result=w.record_review(run,value,independent=True)
    assert result['agent_decision_counts']['unknown']==manifest['review_target_count']
    assert result['program_decision_counts']['unknown']==0
    assert result['program_decision_counts']['supported']==manifest['program_verified_count']
    assert result['decision_counts']['unknown']==manifest['review_target_count']


def test_reports_keep_ordinary_punctuation_but_escape_markdown_and_html():
    comment='OEMetadata 2.0.4 uses CC-BY-4.0.\n# Forged heading\n- forged item\n1. forged list\n<script>bad</script>\n**bold**'
    report=w.render_review_report({'metadata_hash':'fixture','entries':[
        {'pointer':'/title','decision':'unknown','comment':comment,'evidence_ids':[]}]})
    assert 'OEMetadata 2.0.4 uses CC-BY-4.0.' in report
    assert '\n# Forged' not in report and '\n- forged' not in report and '\n1. forged' not in report
    assert '<script>' not in report and '**bold**' not in report
    assert 'Agent judgments: 1; automatic checks: 0.' in report


def test_focused_schema_query_returns_field_semantics_not_the_entire_schema(capsys):
    assert oep_metadata.main(['schema','--pointer','/resources/0/temporal/timeseries/0/start'])==0
    result=json.loads(capsys.readouterr().out)
    assert result['schema']['format']=='date-time'
    assert result['target_version']=='OEMetadata-2.0.4'
    assert 'properties' not in result['schema']
    assert len(json.dumps(result))<1500
    assert oep_metadata.main(['schema','--pointer','/resources/0/licenses/0/name'])==0
    assert 'description' in json.loads(capsys.readouterr().out)['schema']
    assert oep_metadata.main(['schema','--pointer','/resources/0/nonexistent'])==2
    assert 'No schema field' in json.loads(capsys.readouterr().err)['error']
