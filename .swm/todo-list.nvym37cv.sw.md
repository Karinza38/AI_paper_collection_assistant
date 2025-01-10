---
title: Todo List
---
- [ ] Task: Refactor the logic between generation and serve

Current generation and serve function is messy. <SwmToken path="/paper_assistant/api/app.py" pos="88:3:3" line-data="    def index():">`index`</SwmToken> use json output of generate function but it is not refer to the newest paper for days. A idea thoughts is to create a folder to cache the <SwmToken path="/paper_assistant/api/app.py" pos="56:14:16" line-data="        if not os.path.exists(&quot;out/output.json&quot;):">`output.json`</SwmToken> with current date.&nbsp;

Then <SwmPath>[paper_assistant/utils/parse_json_to_md.py](/paper_assistant/utils/parse_json_to_md.py)</SwmPath> can process to output.md&nbsp;

- [ ] &nbsp;

<SwmMeta version="3.0.0" repo-id="Z2l0aHViJTNBJTNBZ3B0X3BhcGVyX2Fzc2lzdGFudCUzQSUzQUR5bGFuTElpaWk=" repo-name="gpt_paper_assistant"><sup>Powered by [Swimm](https://app.swimm.io/)</sup></SwmMeta>
