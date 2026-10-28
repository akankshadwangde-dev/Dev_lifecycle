export interface HelpTopic {
  title: string
  intro: string
  sections: { heading: string; body: string[] }[]
}

export const HELP: Record<string, HelpTopic> = {
  start: {
    title: 'Getting started',
    intro: 'Lifecycle Studio takes a ticket from first analysis to documented solution. People decide at every step; the AI prepares.',
    sections: [
      { heading: 'The flow', body: [
        'Intake: the ticket is read from Jira or the service desk.',
        'Knowledge: the AI searches Confluence, past tickets and the current SAP code, then recommends a solution with its sources.',
        'Impact: who calls the affected objects, open transports, existing unit tests.',
        'Plan: the objects to change, or the RICEFW list for a new requirement.',
        'Build: the AI drafts the code change against the current version in SAP.',
        'Document: draft Confluence pages. After approval they are published and added to the knowledge base, so the next similar ticket is faster.',
      ] },
      { heading: 'Approvals', body: [
        'The flow stops at four points and waits for a person: recommendation, plan, code change, pages.',
        '"Request changes" sends the step back to the AI with your comment.',
        'An incident that needs no code can skip straight to documentation.',
      ] },
      { heading: 'Roles', body: [
        'Pick your role in the top bar. Each role has its own home screen and rights.',
        'Developer: starts new requirements and changes, approves code changes.',
        'AMS consultant: works incidents, can resolve without code, hands code fixes to a developer.',
        'Tech lead: approves plans and publishes Confluence pages.',
        'Solution architect: approves designs for new objects.',
        'Functional consultant and Project manager: read-only views.',
        'Admin: models, connections and the knowledge base.',
      ] },
      { heading: 'Phase 1 limits', body: [
        'Code is not written to SAP yet: copy or download it. Deploy, ATC review and unit test runs arrive in Phase 2.',
        'Sign-in is a role picker; single sign-on arrives in Phase 2.',
      ] },
    ],
  },
  home: {
    title: 'Home',
    intro: 'Your home screen shows what needs you first, then all work in the project.',
    sections: [
      { heading: 'Needs you', body: [
        'Items waiting for a decision you are allowed to make, items you can start, and items that stopped with an error.',
      ] },
      { heading: 'All work', body: [
        'Every ticket in the project. Filter by type. Open a row to see its flow.',
        'Sync pulls new tickets from Jira. In demo mode it uses sample tickets.',
      ] },
    ],
  },
  item: {
    title: 'Working on an item',
    intro: 'The steps at the top show where the item is. Click a finished step to see what the AI produced there.',
    sections: [
      { heading: 'Deciding', body: [
        'When the flow waits for a decision, the buttons appear under the current step.',
        'If your role cannot decide, the bar tells you who can.',
        'Request changes needs a short comment; the AI redoes that step with it.',
      ] },
      { heading: 'Sources', body: [
        'Every recommendation lists the pages, tickets and code it used. Check them before you accept.',
        'Match shows how closely a source matched the ticket text, compared with the best match.',
      ] },
      { heading: 'Code', body: [
        'Build shows only the changed lines against the current code in SAP.',
        'The code follows the syntax allowed on the target release (for example no inline declarations below 7.40).',
        'Copy or download the new source and paste it in ADT or SE80. Writing to SAP comes in Phase 2.',
      ] },
      { heading: 'If something fails', body: [
        'A failed step shows the error and a Retry button. Nothing is lost: the flow resumes from the last finished step.',
      ] },
    ],
  },
  knowledge: {
    title: 'Knowledge',
    intro: 'Everything the AI searches before it recommends anything.',
    sections: [
      { heading: 'Sources', body: [
        'Confluence: pages from the spaces set up under Connections.',
        'Tickets: resolved Jira or service desk tickets with their resolution notes.',
        'Studio: pages published from this tool. This is how the tool learns from every solved ticket.',
      ] },
      { heading: 'Refresh', body: ['Admins can refresh the index. Pages written by the studio are always kept.'] },
    ],
  },
  models: {
    title: 'Models',
    intro: 'Any model your organisation allows can be added here.',
    sections: [
      { heading: 'Adding a model', body: [
        'Provider: Anthropic, OpenAI, Azure OpenAI, AWS Bedrock, Google Vertex AI, or any OpenAI-compatible URL such as vLLM, Ollama or a company gateway.',
        'Model: the provider\'s model name or your deployment name.',
        'Secret: a reference such as env:ANTHROPIC_API_KEY. The key itself is never stored in the tool.',
      ] },
      { heading: 'Data level', body: [
        'Public: documentation only. Code: source code and tickets. Production: production logs and data.',
        'The tool never sends data above a model\'s level, whatever the user picks.',
      ] },
      { heading: 'Which model is used', body: [
        'The model picked in the top bar, if it is allowed for the data. Otherwise the model set as default for that step, then the rest by priority.',
        'If a model fails, the next allowed one takes over.',
      ] },
    ],
  },
  connections: {
    title: 'Connections',
    intro: 'Where the studio reads tickets, documents and code.',
    sections: [
      { heading: 'Types', body: [
        'Jira: Cloud or Data Center. Also covers Jira Service Management.',
        'Confluence: Cloud (URL ends in /wiki) or Data Center. Set the spaces to read and the one space the studio may write to.',
        'SAP (ADT): NetWeaver 7.40 and later, S/4HANA, BTP ABAP. SAP (RFC): older releases; needs the SAP RFC SDK on the server.',
      ] },
      { heading: 'Release profiles', body: [
        'Test a SAP connection to detect its release. Cloud and Full use ADT. Hybrid (7.02–7.31) and Basic (older) read over RFC.',
      ] },
      { heading: 'Secrets', body: ['Enter a reference such as env:JIRA_TOKEN, and set that environment variable on the server.'] },
      { heading: 'Demo mode', body: ['Without a connection of a type, demo mode uses sample data for it.'] },
    ],
  },
  audit: {
    title: 'Audit trail',
    intro: 'Every start, decision, model change and connection change, with who did it and when.',
    sections: [],
  },
}
