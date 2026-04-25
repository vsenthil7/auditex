p = r"C:/Users/v_sen/Documents/Projects/0001_Hack0014_Vertex_Swarm_Tashi/auditex/backend/tests/unit/test_execution_worker.py"
t = open(p, 'r', encoding='utf-8').read()
old = 'patch("db.repositories.event_repo.insert_event", AsyncMock()),'
extra = chr(32)*9 + 'patch("db.repositories.human_oversight_repo.get_policy", AsyncMock(return_value=None)),'
new = old + ' \\' + chr(10) + extra
n = t.count(old)
t = t.replace(old, new)
open(p, 'w', encoding='utf-8').write(t)
print('patched ', n)
