When implementing any task we should create a markdown spec with file format `<SUB_TASK_NAME>-SPEC.md`. This spec file will be crucial in implementing the end goal successfully as it will require multiple tasks / steps that need to be completed by an AI agent with debug help from a senior software dev.

# The workflow spec should have the following sections

## Project details

Pterodactyl server manager, rust game servers, oxide plugins, postgres db, etc

## High Level End Goal

3-5 sentences or bullet points max

## High Level Proposed Solution

3-5 sentences or bullet points max

## Next steps

steps in this should be very detailed and written in a way that an AI agent will be able to utilize in order to complete the required step.

## Current Unresolved Issues

any issues which we know about but have not yet implemented in the spec. These unresolved issues should not be iterated on until the senior dev outlines the required changes

## Change Log

history of changes with detailed descriptions of each change

## Updated Implementation details

outline of end goal for file tree, description of what each file should do once fully implemented

## Current implementation details

file tree, description of each file
Only add section #8 if we are refactoring some current implementation. If this is a new feature we should leave this section out

# “Rules for AI agent” section

Add a “Rules for AI agent” section at the top of the markdown spec as well. Be concise with this as we do not want it to take up too much space in the SPEC, but it is important that these rules are followed so ensure that all required details are present.

1. Do not change the structure or delete sections from the markdown spec, only add into it
2. Do not over-complicate things, make sure that this is in the spec as well. We should favor simple solutions to complex flows rather than jumping to abstractions. Consult me if we need to do anything overly-complex
3. If a file is indented > ~5-6 times, we almost certainly need to create some new function or class to handle the logic
4. For rust oxide plugins, we have to keep the plugin logic in one single file most of the time as importing other files is more complicated than it is worth due to the sandboxing of the plugin environments
5. Before attempting to implement logic that requires file changes or db schema changes, check in with the senior software dev to ensure that this is the correct approach
6. Document all assumptions made during implementation in the Current Implementation Details section
7. When making significant architectural decisions, document the reasoning in the Change Log section
8. Do NOT implement tests unless specifically requested. Instead, suggest when manual review by the senior software dev would be beneficial
9. Always update the SPEC file with each change being made to maintain accurate documentation
10. Before implementing changes, review the Previous Implementation Overview section and examine the referenced files to ensure a complete understanding of the existing system
11. As the AI agent you are crucial in this workflow and need to make decisions that are good for the longevity of the project while not over-abstracting and over-complicating things
