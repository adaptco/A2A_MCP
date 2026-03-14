When implementing any task we should create a markdown spec with file format `<SUB_TASK_NAME>-SPEC.md`. This spec file will be crucial in implementing the end goal successfully as it will require multiple tasks / steps that need to be completed by an AI agent with debug help from a senior software dev.

# The workflow spec should have the following sections

## Project details

NextJS 15, tailwind, drizzle, server actions instead of API routes, framer motion, etc
utilize the @package.json to get the exact versions of each package and the @tailwind.config.ts for our styling config and the @tsconfig.json for our project config

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

Add a “Rules for AI agent” section at the top of the markdown spec.
Be concise with this as we do not want it to take up too much space in the SPEC, but it is important that these rules are followed so ensure that all required details are present.

1. Do not change the structure or delete sections from the markdown spec, only add into it
2. use NextJS 15 server actions. do not use API routes. utilize @Web if needed for context on server actions and their usage
3. focus on re-usability. We should be able to easily utilize the "wrapper" / "container" components to create other similar pages
4. Do not over-complicate things, make sure that this is in the spec as well. We should favor simple solutions to complex flows rather than jumping to abstractions
5. Consult me (Senior Dev) if we need to do anything overly-complex
6. If a file is indented > ~5-6 times, we almost certainly need to create some "wrapper" / "container" component
7. As the AI agent you are crucial in this workflow and need to make decisions that are good for the longevity of the project while not over-abstracting and over-complicating things
