# Deep Research Modes

Mode guidance now lives one file per mode under [`modes/`](modes/README.md). Start with [`modes/README.md`](modes/README.md) for the routing table, then read the file for the chosen mode in full before retrieval.

Each mode file follows the same skeleton—choose-when, evidence hierarchy, decomposition pattern, gates, output sections, completion criteria, pitfalls—and its **Output sections** list is the exact `report.md` skeleton that `reportctl.py init --mode <mode>` scaffolds. A framework test keeps the two in sync.
