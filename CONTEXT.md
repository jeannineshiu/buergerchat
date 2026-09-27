# buergerchat

A chatbot that explains German government services in plain language, citing official sources, and names the responsible authority for a person's location.

## Language

### A conversation

**Turn**:
One user message together with the conversation before it.
_Avoid_: request, query (for the whole turn)

**Turn plan**:
The decision about how a turn is answered: its turn kind, topic, authority outcome and retrieval query.
_Avoid_: routing result, flags

**Turn kind**:
The way a turn is answered: small talk, a question about the bot itself (meta), asking back what the matter is about, or a retrieved answer.
_Avoid_: mode, intent

**Topic**:
The benefit area a turn is about (Bürgergeld, Kindergeld, Wohngeld, Rente, Aufenthalt, …), or `allgemein` when none is recognised.
_Avoid_: category, theme

**Retrieval query**:
The text searched against the knowledge base: usually the message itself, the previous question plus the message for short follow-ups.

### Authorities

**Behörde**:
The office responsible for a service at a given place (Jobcenter, Familienkasse, Bürgeramt, …).
_Avoid_: agency, office, authority (in German-facing text)

**PLZ**:
A German five-digit postcode; together with a topic it is what locates the responsible Behörde.
_Avoid_: zip code, postal code

**Behörden-Finder**:
The live lookup of the responsible Behörde in the official PVOG directory.
_Avoid_: authority search, PVOG (for the lookup as a whole)

**Authority outcome**:
What a turn's answer says about the responsible Behörde: not asked for, needs a PLZ first, found, or not found.

### Answers and sources

**Source**:
The smallest separately linkable part of an official text that an answer draws on (a page, or a single § of a law), listed with the answer so the reader can check the original. A page that was retrieved but not used in the answer is not a source; a Behörde's website is a source when the answer names that Behörde. The same article published at several addresses (e.g. once per local office) is one source; when the reader has given a PLZ and a copy exists for the office responsible for that place, that copy is the one listed.
_Avoid_: reference, retrieved page, context (for the listed pages)

**Publisher**:
The official website a page was crawled from (Bundesagentur für Arbeit, gesetze-im-internet.de, service.berlin.de, …). Never shown to the reader.
_Avoid_: source (for the website)
