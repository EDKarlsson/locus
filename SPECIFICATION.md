# Project: Agent Memory Palace Skill

## Pretext

Since starting with homelab-iac and newer projects, agent-control-plane, and homelab-as-production. 
I have had claude use a memory technique to keep information handy but context windows small.

## Intent

I want to expand on this idea and build a Memory Palace skill. Luckily there is no limit to how deep the memory
can go using markdown files and directories. The idea is to keep a context window as small as possible while 
referencing the precise information that can be used.

## Guidelines

1. Should use markdown files and directories.
2. This should be usable by any kind of agent.
    - Meaning, the information and prompts in the skill can be understood generally by AI
3. Flexible and expandable.
4. Reference current commands and skills located in
    - ~/.claude/{skills, commands}
    - /home/dank/.claude/projects/-home-dank-git-valhalla-homelab-iac/memory
    - ~/.codex/skills
    - ~/git/valhalla/homelab-iac
      - `.codex`
      - `.gemini`
      - `.claude`
    - ~/git/valhalla/agent-control-plane
      - `.codex`
      - `.gemini`
      - `.claude`
    
## Process

1. Full project analysis
2. Generate as many questions as possible to get more insight on goals and milestones.
3. Develop a project plan in a new Github Repo
    - The project plan should be exported to one of these 3, based on your best judgement.
        - Github
        - Gitlab
        - YouTrack
4. Break down work into multiple phases and tasks
    - These should map the project plan interface
5. Code should be reviewed by muliple agents on github an locally. Needs to cover:
    - Unit Tests
    - Code coverage
    - Architecture analysis
    - Cyber Security analysis and testnig
    - Possibly some kind of integration testing.
6. Leverage the local Gemini, Codex, and Claude applications.

## Extras

- [How to build a memory palace](https://artofmemory.com/blog/how-to-build-a-memory-palace/)
- [Method of Loci](https://en.wikipedia.org/wiki/Method_of_loci)
- [How to build a memory palact to store and revisit information](https://psyche.co/guides/how-to-build-a-memory-palace-to-store-and-revisit-information)
