# MANUSCRIPT ORIGINALITY AUDIT

## 1. Potentially Formulaic Passages
- **Abstract Opening:** "Microservice architectures decompose monolithic systems..." (Standard, but necessary context).
- **Introduction Context:** "Because executing empirical fault injection across hundreds of services is prohibitively expensive..." (Common justification for static analysis).

## 2. Passages Requiring Manual Similarity Checking
- Section 2.1 description of dynamic Service Dependency Graphs (SDGs) and Jaeger/Zipkin functionality. Concepts are universal, but wording should be checked against tracing literature.
- Section 4.3 description of Pumba fault modalities (SIGKILL, tc netem, stress-ng). Technical descriptions are highly constrained by the tools themselves.

## 3. Literature-Derived Ideas Requiring Citations
- The concept of target leakage in ML models applied to SE (needs general ML/SE citation).
- The historical shift from static code analysis (Zimmermann et al.) to dynamic distributed graphs.
- Epidemic models of queue saturation (Chen et al.).

## 4. Reused Terminology (To be Preserved)
- "Service Dependency Graph (SDG)"
- "Blast Radius"
- "Chaos Engineering"
- "DeathStarBench"
- "False Negative"
