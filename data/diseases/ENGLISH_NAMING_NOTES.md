# English naming review

Review date: 2026-10-25. Original research date: 2026-10-23.

The four source datasets have been converted to English, including filenames, disease titles, field labels, narratives, and Korean portions of schema keys. Established English disease names were selected using the host crop and pathogen, then checked against APS, EPPO, IRRI, and extension/research sources. An automated translation draft was followed by terminology corrections and editorial review. Existing scientific names and historical synonyms remain associated with their sources; this is not a full taxonomic or regulatory revision.

The original `checked_date`, record numbers, source URL lists, and uncertainty flags are retained. `official_kr_name` remains for compatibility: its value is an English rendering of the disease label or naming-status statement in Korean sources. It does not imply that a Korean agency has designated an official English name. `contains_unverified` and the CSV column `fields_with_unverified` replace the former mixed-language keys. Source URLs, including a Korean-language legal URL, are opaque identifiers and are preserved.

Unverified occurrence does not mean absence. Unverified image rights do not grant permission. Existing quarantine and image-license statements remain the original research snapshot; the English naming review is not a fresh audit of every regulatory or licensing claim.

## Names used

| Record | Crop | English disease name | Naming reference |
| --- | --- | --- | --- |
| 1 | Rice | Rice blast | [Reference](https://gd.eppo.int/taxon/PYRIOR) |
| 2 | Rice | Sheath blight | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Rice.aspx) |
| 3 | Rice | Brown spot | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Rice.aspx) |
| 4 | Rice | Bacterial blight | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Rice.aspx) |
| 5 | Rice | Bacterial leaf streak | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Rice.aspx) |
| 6 | Rice | Bakanae disease | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Rice.aspx) |
| 7 | Rice | False smut | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Rice.aspx) |
| 8 | Rice | Bacterial panicle blight / bacterial grain rot | [Reference](https://www.lsuagcenter.com/topics/crops/rice/diseases/photos/bacterial-panicle-blight) |
| 9 | Rice | Rice stripe | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Rice.aspx) |
| 10 | Rice | Rice dwarf | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Rice.aspx) |
| 11 | Rice | Udbatta disease | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Rice.aspx) |
| 12 | Rice | Ufra disease | [Reference](https://gd.eppo.int/taxon/DITYAN) |
| 13 | Corn | Northern corn leaf blight | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Corn.aspx) |
| 14 | Corn | Southern corn leaf blight | [Reference](https://gd.eppo.int/taxon/COCHHE) |
| 15 | Corn | Gray leaf spot | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Corn.aspx) |
| 16 | Corn | Common rust | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Corn.aspx) |
| 17 | Corn | Southern rust | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Corn.aspx) |
| 18 | Corn | Common smut | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Corn.aspx) |
| 19 | Corn | Head smut | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Corn.aspx) |
| 20 | Corn | Fusarium ear rot | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Corn.aspx) |
| 21 | Corn | Gibberella ear rot | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Corn.aspx) |
| 22 | Corn | Stewart’s bacterial wilt | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Corn.aspx) |
| 23 | Corn | Goss’s bacterial wilt and leaf blight | [Reference](https://www.apsnet.org/edcenter/resources/commonnames/Pages/Corn.aspx) |
| 24 | Corn | Philippine downy mildew | [Reference](https://gd.eppo.int/taxon/PRSCPH) |
| 25 | Corn | Brown stripe downy mildew | [Reference](https://gd.eppo.int/taxon/SCPHRZ) |
| 26 | Corn | Maize lethal necrosis | [Reference](https://www.cimmyt.org/news/promising-cimmyt-maize-inbreds-and-pre-commercial-hybrids-identified-against-maize-lethal-necrosis-mln/) |

## Important distinctions

- Rice brown spot (*Bipolaris oryzae*) and southern corn leaf blight (*B. maydis*) share a Korean disease label but require different English names.
- Bakanae disease, false smut, udbatta disease, and ufra disease use established English names rather than literal translations of Korean descriptions.
- Common smut and head smut are distinct corn diseases. Rice kernel smut is a different disease again. Smut teliospores are identified as such where appropriate.
- Fusarium ear rot and Gibberella ear rot are distinguished by their pathogen groups and affected organ; a generic Korean ear-rot label does not establish the causal species. The original inference and uncertainty for the Nongsaro Fusarium-ear-rot correspondence are retained.
- Maize lethal necrosis requires MCMV coinfection with a virus in the family Potyviridae. WSMV belongs to genus Tritimovirus, so the broader family is used when the examples include WSMV.
- English descriptions of minor Korean sclerotial-disease labels are marked as descriptive where a standardized English common name was not verified.

Additional naming references: [IRRI rice disease contents](https://rice-diseases.irri.org/contents), [Cornell sweet corn diseases](https://www.vegetables.cornell.edu/pest-management/disease-factsheets/sweet-corn-diseases-and-control-measures/), and [APS corn compendium contents](https://apsjournals.apsnet.org/doi/10.1094/9780890544945.002).
