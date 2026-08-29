# Suspect item adjudication

Four of the five gpt-5-nano matching errors carry one verbatim rationale asserting the
criterion predicate IS present while gold says not_met. For each item below decide:

- **A — item is mislabelled.** The record states the predicate; gold is wrong. Fix the
  generator, rescore, and remove the error from the taxonomy.
- **B — item is underspecified.** The record neither states nor denies the predicate, so
  the item is unanswerable. Remove it from the set; it measures nothing.
- **C — genuine model error.** The record contains the distinguishing evidence and the
  model missed it. Keep it and record the taxonomy category.

Verdict C is the only one that may be reported as a reasoning failure in Sec. 7.3.

## `match:ALCOHOL-ABUSE:000`  (gold: **not_met**)

```json
{
  "item_id": "match:ALCOHOL-ABUSE:000",
  "task": "matching",
  "criterion": {
    "schema_version": "0.1.0",
    "criterion_id": "n2c2:ALCOHOL-ABUSE",
    "source": "n2c2_2018",
    "polarity": "inclusion",
    "text": "Current alcohol use over the weekly recommended limit.",
    "expression": {
      "node_type": "atom",
      "entity": {
        "text": "alcohol abuse",
        "type": "lifestyle",
        "codes": {}
      },
      "temporal": {
        "operator": "current",
        "value": null,
        "unit": null,
        "anchor": "enrollment"
      },
      "numeric": null
    },
    "metadata": {
      "tag": "ALCOHOL-ABUSE"
    }
  },
  "facts": {
    "record_id": "ALCOHOL-ABUSE-P000",
    "facts": {
      "alcohol abuse": {
        "present": true,
        "value": null,
        "days_ago": null,
        "current": false
      }
    }
  },
  "gold": false,
  "group": "ALCOHOL-ABUSE",
  "depth": null
}
```

Criterion:

```json
{
  "schema_version": "0.1.0",
  "criterion_id": "n2c2:ALCOHOL-ABUSE",
  "source": "n2c2_2018",
  "polarity": "inclusion",
  "text": "Current alcohol use over the weekly recommended limit.",
  "expression": {
    "node_type": "atom",
    "entity": {
      "text": "alcohol abuse",
      "type": "lifestyle",
      "codes": {}
    },
    "temporal": {
      "operator": "current",
      "value": null,
      "unit": null,
      "anchor": "enrollment"
    },
    "numeric": null
  },
  "metadata": {
    "tag": "ALCOHOL-ABUSE"
  }
}
```

**Verdict (A / B / C):** 

**Reasoning:** 

---

## `match:ALCOHOL-ABUSE:001`  (gold: **not_met**)

```json
{
  "item_id": "match:ALCOHOL-ABUSE:001",
  "task": "matching",
  "criterion": {
    "schema_version": "0.1.0",
    "criterion_id": "n2c2:ALCOHOL-ABUSE",
    "source": "n2c2_2018",
    "polarity": "inclusion",
    "text": "Current alcohol use over the weekly recommended limit.",
    "expression": {
      "node_type": "atom",
      "entity": {
        "text": "alcohol abuse",
        "type": "lifestyle",
        "codes": {}
      },
      "temporal": {
        "operator": "current",
        "value": null,
        "unit": null,
        "anchor": "enrollment"
      },
      "numeric": null
    },
    "metadata": {
      "tag": "ALCOHOL-ABUSE"
    }
  },
  "facts": {
    "record_id": "ALCOHOL-ABUSE-P001",
    "facts": {}
  },
  "gold": false,
  "group": "ALCOHOL-ABUSE",
  "depth": null
}
```

Criterion:

```json
{
  "schema_version": "0.1.0",
  "criterion_id": "n2c2:ALCOHOL-ABUSE",
  "source": "n2c2_2018",
  "polarity": "inclusion",
  "text": "Current alcohol use over the weekly recommended limit.",
  "expression": {
    "node_type": "atom",
    "entity": {
      "text": "alcohol abuse",
      "type": "lifestyle",
      "codes": {}
    },
    "temporal": {
      "operator": "current",
      "value": null,
      "unit": null,
      "anchor": "enrollment"
    },
    "numeric": null
  },
  "metadata": {
    "tag": "ALCOHOL-ABUSE"
  }
}
```

**Verdict (A / B / C):** 

**Reasoning:** 

---

## `match:ALCOHOL-ABUSE:002`  (gold: **not_met**)

```json
{
  "item_id": "match:ALCOHOL-ABUSE:002",
  "task": "matching",
  "criterion": {
    "schema_version": "0.1.0",
    "criterion_id": "n2c2:ALCOHOL-ABUSE",
    "source": "n2c2_2018",
    "polarity": "inclusion",
    "text": "Current alcohol use over the weekly recommended limit.",
    "expression": {
      "node_type": "atom",
      "entity": {
        "text": "alcohol abuse",
        "type": "lifestyle",
        "codes": {}
      },
      "temporal": {
        "operator": "current",
        "value": null,
        "unit": null,
        "anchor": "enrollment"
      },
      "numeric": null
    },
    "metadata": {
      "tag": "ALCOHOL-ABUSE"
    }
  },
  "facts": {
    "record_id": "ALCOHOL-ABUSE-P002",
    "facts": {}
  },
  "gold": false,
  "group": "ALCOHOL-ABUSE",
  "depth": null
}
```

Criterion:

```json
{
  "schema_version": "0.1.0",
  "criterion_id": "n2c2:ALCOHOL-ABUSE",
  "source": "n2c2_2018",
  "polarity": "inclusion",
  "text": "Current alcohol use over the weekly recommended limit.",
  "expression": {
    "node_type": "atom",
    "entity": {
      "text": "alcohol abuse",
      "type": "lifestyle",
      "codes": {}
    },
    "temporal": {
      "operator": "current",
      "value": null,
      "unit": null,
      "anchor": "enrollment"
    },
    "numeric": null
  },
  "metadata": {
    "tag": "ALCOHOL-ABUSE"
  }
}
```

**Verdict (A / B / C):** 

**Reasoning:** 

---

## `match:ALCOHOL-ABUSE:003`  (gold: **met**)

```json
{
  "item_id": "match:ALCOHOL-ABUSE:003",
  "task": "matching",
  "criterion": {
    "schema_version": "0.1.0",
    "criterion_id": "n2c2:ALCOHOL-ABUSE",
    "source": "n2c2_2018",
    "polarity": "inclusion",
    "text": "Current alcohol use over the weekly recommended limit.",
    "expression": {
      "node_type": "atom",
      "entity": {
        "text": "alcohol abuse",
        "type": "lifestyle",
        "codes": {}
      },
      "temporal": {
        "operator": "current",
        "value": null,
        "unit": null,
        "anchor": "enrollment"
      },
      "numeric": null
    },
    "metadata": {
      "tag": "ALCOHOL-ABUSE"
    }
  },
  "facts": {
    "record_id": "ALCOHOL-ABUSE-P003",
    "facts": {
      "alcohol abuse": {
        "present": true,
        "value": null,
        "days_ago": null,
        "current": true
      }
    }
  },
  "gold": true,
  "group": "ALCOHOL-ABUSE",
  "depth": null
}
```

Criterion:

```json
{
  "schema_version": "0.1.0",
  "criterion_id": "n2c2:ALCOHOL-ABUSE",
  "source": "n2c2_2018",
  "polarity": "inclusion",
  "text": "Current alcohol use over the weekly recommended limit.",
  "expression": {
    "node_type": "atom",
    "entity": {
      "text": "alcohol abuse",
      "type": "lifestyle",
      "codes": {}
    },
    "temporal": {
      "operator": "current",
      "value": null,
      "unit": null,
      "anchor": "enrollment"
    },
    "numeric": null
  },
  "metadata": {
    "tag": "ALCOHOL-ABUSE"
  }
}
```

**Verdict (A / B / C):** 

**Reasoning:** 

---

## `match:ALCOHOL-ABUSE:004`  (gold: **met**)

```json
{
  "item_id": "match:ALCOHOL-ABUSE:004",
  "task": "matching",
  "criterion": {
    "schema_version": "0.1.0",
    "criterion_id": "n2c2:ALCOHOL-ABUSE",
    "source": "n2c2_2018",
    "polarity": "inclusion",
    "text": "Current alcohol use over the weekly recommended limit.",
    "expression": {
      "node_type": "atom",
      "entity": {
        "text": "alcohol abuse",
        "type": "lifestyle",
        "codes": {}
      },
      "temporal": {
        "operator": "current",
        "value": null,
        "unit": null,
        "anchor": "enrollment"
      },
      "numeric": null
    },
    "metadata": {
      "tag": "ALCOHOL-ABUSE"
    }
  },
  "facts": {
    "record_id": "ALCOHOL-ABUSE-P004",
    "facts": {
      "alcohol abuse": {
        "present": true,
        "value": null,
        "days_ago": null,
        "current": true
      }
    }
  },
  "gold": true,
  "group": "ALCOHOL-ABUSE",
  "depth": null
}
```

Criterion:

```json
{
  "schema_version": "0.1.0",
  "criterion_id": "n2c2:ALCOHOL-ABUSE",
  "source": "n2c2_2018",
  "polarity": "inclusion",
  "text": "Current alcohol use over the weekly recommended limit.",
  "expression": {
    "node_type": "atom",
    "entity": {
      "text": "alcohol abuse",
      "type": "lifestyle",
      "codes": {}
    },
    "temporal": {
      "operator": "current",
      "value": null,
      "unit": null,
      "anchor": "enrollment"
    },
    "numeric": null
  },
  "metadata": {
    "tag": "ALCOHOL-ABUSE"
  }
}
```

**Verdict (A / B / C):** 

**Reasoning:** 

---

## `match:ALCOHOL-ABUSE:005`  (gold: **met**)

```json
{
  "item_id": "match:ALCOHOL-ABUSE:005",
  "task": "matching",
  "criterion": {
    "schema_version": "0.1.0",
    "criterion_id": "n2c2:ALCOHOL-ABUSE",
    "source": "n2c2_2018",
    "polarity": "inclusion",
    "text": "Current alcohol use over the weekly recommended limit.",
    "expression": {
      "node_type": "atom",
      "entity": {
        "text": "alcohol abuse",
        "type": "lifestyle",
        "codes": {}
      },
      "temporal": {
        "operator": "current",
        "value": null,
        "unit": null,
        "anchor": "enrollment"
      },
      "numeric": null
    },
    "metadata": {
      "tag": "ALCOHOL-ABUSE"
    }
  },
  "facts": {
    "record_id": "ALCOHOL-ABUSE-P005",
    "facts": {
      "alcohol abuse": {
        "present": true,
        "value": null,
        "days_ago": null,
        "current": true
      }
    }
  },
  "gold": true,
  "group": "ALCOHOL-ABUSE",
  "depth": null
}
```

Criterion:

```json
{
  "schema_version": "0.1.0",
  "criterion_id": "n2c2:ALCOHOL-ABUSE",
  "source": "n2c2_2018",
  "polarity": "inclusion",
  "text": "Current alcohol use over the weekly recommended limit.",
  "expression": {
    "node_type": "atom",
    "entity": {
      "text": "alcohol abuse",
      "type": "lifestyle",
      "codes": {}
    },
    "temporal": {
      "operator": "current",
      "value": null,
      "unit": null,
      "anchor": "enrollment"
    },
    "numeric": null
  },
  "metadata": {
    "tag": "ALCOHOL-ABUSE"
  }
}
```

**Verdict (A / B / C):** 

**Reasoning:** 

---

## `match:ALCOHOL-ABUSE:006`  (gold: **met**)

```json
{
  "item_id": "match:ALCOHOL-ABUSE:006",
  "task": "matching",
  "criterion": {
    "schema_version": "0.1.0",
    "criterion_id": "n2c2:ALCOHOL-ABUSE",
    "source": "n2c2_2018",
    "polarity": "inclusion",
    "text": "Current alcohol use over the weekly recommended limit.",
    "expression": {
      "node_type": "atom",
      "entity": {
        "text": "alcohol abuse",
        "type": "lifestyle",
        "codes": {}
      },
      "temporal": {
        "operator": "current",
        "value": null,
        "unit": null,
        "anchor": "enrollment"
      },
      "numeric": null
    },
    "metadata": {
      "tag": "ALCOHOL-ABUSE"
    }
  },
  "facts": {
    "record_id": "ALCOHOL-ABUSE-P006",
    "facts": {
      "alcohol abuse": {
        "present": true,
        "value": null,
        "days_ago": null,
        "current": true
      }
    }
  },
  "gold": true,
  "group": "ALCOHOL-ABUSE",
  "depth": null
}
```

Criterion:

```json
{
  "schema_version": "0.1.0",
  "criterion_id": "n2c2:ALCOHOL-ABUSE",
  "source": "n2c2_2018",
  "polarity": "inclusion",
  "text": "Current alcohol use over the weekly recommended limit.",
  "expression": {
    "node_type": "atom",
    "entity": {
      "text": "alcohol abuse",
      "type": "lifestyle",
      "codes": {}
    },
    "temporal": {
      "operator": "current",
      "value": null,
      "unit": null,
      "anchor": "enrollment"
    },
    "numeric": null
  },
  "metadata": {
    "tag": "ALCOHOL-ABUSE"
  }
}
```

**Verdict (A / B / C):** 

**Reasoning:** 

---

## `match:ALCOHOL-ABUSE:007`  (gold: **not_met**)

```json
{
  "item_id": "match:ALCOHOL-ABUSE:007",
  "task": "matching",
  "criterion": {
    "schema_version": "0.1.0",
    "criterion_id": "n2c2:ALCOHOL-ABUSE",
    "source": "n2c2_2018",
    "polarity": "inclusion",
    "text": "Current alcohol use over the weekly recommended limit.",
    "expression": {
      "node_type": "atom",
      "entity": {
        "text": "alcohol abuse",
        "type": "lifestyle",
        "codes": {}
      },
      "temporal": {
        "operator": "current",
        "value": null,
        "unit": null,
        "anchor": "enrollment"
      },
      "numeric": null
    },
    "metadata": {
      "tag": "ALCOHOL-ABUSE"
    }
  },
  "facts": {
    "record_id": "ALCOHOL-ABUSE-P007",
    "facts": {}
  },
  "gold": false,
  "group": "ALCOHOL-ABUSE",
  "depth": null
}
```

Criterion:

```json
{
  "schema_version": "0.1.0",
  "criterion_id": "n2c2:ALCOHOL-ABUSE",
  "source": "n2c2_2018",
  "polarity": "inclusion",
  "text": "Current alcohol use over the weekly recommended limit.",
  "expression": {
    "node_type": "atom",
    "entity": {
      "text": "alcohol abuse",
      "type": "lifestyle",
      "codes": {}
    },
    "temporal": {
      "operator": "current",
      "value": null,
      "unit": null,
      "anchor": "enrollment"
    },
    "numeric": null
  },
  "metadata": {
    "tag": "ALCOHOL-ABUSE"
  }
}
```

**Verdict (A / B / C):** 

**Reasoning:** 

---

## `match:ASP-FOR-MI:000`  (gold: **not_met**)

```json
{
  "item_id": "match:ASP-FOR-MI:000",
  "task": "matching",
  "criterion": {
    "schema_version": "0.1.0",
    "criterion_id": "n2c2:ASP-FOR-MI",
    "source": "n2c2_2018",
    "polarity": "inclusion",
    "text": "Use of aspirin to prevent myocardial infarction.",
    "expression": {
      "node_type": "atom",
      "entity": {
        "text": "aspirin for mi prophylaxis",
        "type": "drug",
        "codes": {}
      },
      "temporal": {
        "operator": "current",
        "value": null,
        "unit": null,
        "anchor": "enrollment"
      },
      "numeric": null
    },
    "metadata": {
      "tag": "ASP-FOR-MI"
    }
  },
  "facts": {
    "record_id": "ASP-FOR-MI-P000",
    "facts": {
      "aspirin for mi prophylaxis": {
        "present": true,
        "value": null,
        "days_ago": null,
        "current": false
      }
    }
  },
  "gold": false,
  "group": "ASP-FOR-MI",
  "depth": null
}
```

Criterion:

```json
{
  "schema_version": "0.1.0",
  "criterion_id": "n2c2:ASP-FOR-MI",
  "source": "n2c2_2018",
  "polarity": "inclusion",
  "text": "Use of aspirin to prevent myocardial infarction.",
  "expression": {
    "node_type": "atom",
    "entity": {
      "text": "aspirin for mi prophylaxis",
      "type": "drug",
      "codes": {}
    },
    "temporal": {
      "operator": "current",
      "value": null,
      "unit": null,
      "anchor": "enrollment"
    },
    "numeric": null
  },
  "metadata": {
    "tag": "ASP-FOR-MI"
  }
}
```

**Verdict (A / B / C):** 

**Reasoning:** 

---

## `match:ASP-FOR-MI:001`  (gold: **not_met**)

```json
{
  "item_id": "match:ASP-FOR-MI:001",
  "task": "matching",
  "criterion": {
    "schema_version": "0.1.0",
    "criterion_id": "n2c2:ASP-FOR-MI",
    "source": "n2c2_2018",
    "polarity": "inclusion",
    "text": "Use of aspirin to prevent myocardial infarction.",
    "expression": {
      "node_type": "atom",
      "entity": {
        "text": "aspirin for mi prophylaxis",
        "type": "drug",
        "codes": {}
      },
      "temporal": {
        "operator": "current",
        "value": null,
        "unit": null,
        "anchor": "enrollment"
      },
      "numeric": null
    },
    "metadata": {
      "tag": "ASP-FOR-MI"
    }
  },
  "facts": {
    "record_id": "ASP-FOR-MI-P001",
    "facts": {
      "aspirin for mi prophylaxis": {
        "present": true,
        "value": null,
        "days_ago": null,
        "current": false
      }
    }
  },
  "gold": false,
  "group": "ASP-FOR-MI",
  "depth": null
}
```

Criterion:

```json
{
  "schema_version": "0.1.0",
  "criterion_id": "n2c2:ASP-FOR-MI",
  "source": "n2c2_2018",
  "polarity": "inclusion",
  "text": "Use of aspirin to prevent myocardial infarction.",
  "expression": {
    "node_type": "atom",
    "entity": {
      "text": "aspirin for mi prophylaxis",
      "type": "drug",
      "codes": {}
    },
    "temporal": {
      "operator": "current",
      "value": null,
      "unit": null,
      "anchor": "enrollment"
    },
    "numeric": null
  },
  "metadata": {
    "tag": "ASP-FOR-MI"
  }
}
```

**Verdict (A / B / C):** 

**Reasoning:** 

---

## `match:ASP-FOR-MI:002`  (gold: **not_met**)

```json
{
  "item_id": "match:ASP-FOR-MI:002",
  "task": "matching",
  "criterion": {
    "schema_version": "0.1.0",
    "criterion_id": "n2c2:ASP-FOR-MI",
    "source": "n2c2_2018",
    "polarity": "inclusion",
    "text": "Use of aspirin to prevent myocardial infarction.",
    "expression": {
      "node_type": "atom",
      "entity": {
        "text": "aspirin for mi prophylaxis",
        "type": "drug",
        "codes": {}
      },
      "temporal": {
        "operator": "current",
        "value": null,
        "unit": null,
        "anchor": "enrollment"
      },
      "numeric": null
    },
    "metadata": {
      "tag": "ASP-FOR-MI"
    }
  },
  "facts": {
    "record_id": "ASP-FOR-MI-P002",
    "facts": {
      "aspirin for mi prophylaxis": {
        "present": false,
        "value": null,
        "days_ago": null,
        "current": false
      }
    }
  },
  "gold": false,
  "group": "ASP-FOR-MI",
  "depth": null
}
```

Criterion:

```json
{
  "schema_version": "0.1.0",
  "criterion_id": "n2c2:ASP-FOR-MI",
  "source": "n2c2_2018",
  "polarity": "inclusion",
  "text": "Use of aspirin to prevent myocardial infarction.",
  "expression": {
    "node_type": "atom",
    "entity": {
      "text": "aspirin for mi prophylaxis",
      "type": "drug",
      "codes": {}
    },
    "temporal": {
      "operator": "current",
      "value": null,
      "unit": null,
      "anchor": "enrollment"
    },
    "numeric": null
  },
  "metadata": {
    "tag": "ASP-FOR-MI"
  }
}
```

**Verdict (A / B / C):** 

**Reasoning:** 

---

## `match:ASP-FOR-MI:003`  (gold: **not_met**)

```json
{
  "item_id": "match:ASP-FOR-MI:003",
  "task": "matching",
  "criterion": {
    "schema_version": "0.1.0",
    "criterion_id": "n2c2:ASP-FOR-MI",
    "source": "n2c2_2018",
    "polarity": "inclusion",
    "text": "Use of aspirin to prevent myocardial infarction.",
    "expression": {
      "node_type": "atom",
      "entity": {
        "text": "aspirin for mi prophylaxis",
        "type": "drug",
        "codes": {}
      },
      "temporal": {
        "operator": "current",
        "value": null,
        "unit": null,
        "anchor": "enrollment"
      },
      "numeric": null
    },
    "metadata": {
      "tag": "ASP-FOR-MI"
    }
  },
  "facts": {
    "record_id": "ASP-FOR-MI-P003",
    "facts": {
      "aspirin for mi prophylaxis": {
        "present": true,
        "value": null,
        "days_ago": null,
        "current": false
      }
    }
  },
  "gold": false,
  "group": "ASP-FOR-MI",
  "depth": null
}
```

Criterion:

```json
{
  "schema_version": "0.1.0",
  "criterion_id": "n2c2:ASP-FOR-MI",
  "source": "n2c2_2018",
  "polarity": "inclusion",
  "text": "Use of aspirin to prevent myocardial infarction.",
  "expression": {
    "node_type": "atom",
    "entity": {
      "text": "aspirin for mi prophylaxis",
      "type": "drug",
      "codes": {}
    },
    "temporal": {
      "operator": "current",
      "value": null,
      "unit": null,
      "anchor": "enrollment"
    },
    "numeric": null
  },
  "metadata": {
    "tag": "ASP-FOR-MI"
  }
}
```

**Verdict (A / B / C):** 

**Reasoning:** 

---

## `match:ASP-FOR-MI:004`  (gold: **met**)

```json
{
  "item_id": "match:ASP-FOR-MI:004",
  "task": "matching",
  "criterion": {
    "schema_version": "0.1.0",
    "criterion_id": "n2c2:ASP-FOR-MI",
    "source": "n2c2_2018",
    "polarity": "inclusion",
    "text": "Use of aspirin to prevent myocardial infarction.",
    "expression": {
      "node_type": "atom",
      "entity": {
        "text": "aspirin for mi prophylaxis",
        "type": "drug",
        "codes": {}
      },
      "temporal": {
        "operator": "current",
        "value": null,
        "unit": null,
        "anchor": "enrollment"
      },
      "numeric": null
    },
    "metadata": {
      "tag": "ASP-FOR-MI"
    }
  },
  "facts": {
    "record_id": "ASP-FOR-MI-P004",
    "facts": {
      "aspirin for mi prophylaxis": {
        "present": true,
        "value": null,
        "days_ago": null,
        "current": true
      }
    }
  },
  "gold": true,
  "group": "ASP-FOR-MI",
  "depth": null
}
```

Criterion:

```json
{
  "schema_version": "0.1.0",
  "criterion_id": "n2c2:ASP-FOR-MI",
  "source": "n2c2_2018",
  "polarity": "inclusion",
  "text": "Use of aspirin to prevent myocardial infarction.",
  "expression": {
    "node_type": "atom",
    "entity": {
      "text": "aspirin for mi prophylaxis",
      "type": "drug",
      "codes": {}
    },
    "temporal": {
      "operator": "current",
      "value": null,
      "unit": null,
      "anchor": "enrollment"
    },
    "numeric": null
  },
  "metadata": {
    "tag": "ASP-FOR-MI"
  }
}
```

**Verdict (A / B / C):** 

**Reasoning:** 

---

## `match:ASP-FOR-MI:005`  (gold: **met**)

```json
{
  "item_id": "match:ASP-FOR-MI:005",
  "task": "matching",
  "criterion": {
    "schema_version": "0.1.0",
    "criterion_id": "n2c2:ASP-FOR-MI",
    "source": "n2c2_2018",
    "polarity": "inclusion",
    "text": "Use of aspirin to prevent myocardial infarction.",
    "expression": {
      "node_type": "atom",
      "entity": {
        "text": "aspirin for mi prophylaxis",
        "type": "drug",
        "codes": {}
      },
      "temporal": {
        "operator": "current",
        "value": null,
        "unit": null,
        "anchor": "enrollment"
      },
      "numeric": null
    },
    "metadata": {
      "tag": "ASP-FOR-MI"
    }
  },
  "facts": {
    "record_id": "ASP-FOR-MI-P005",
    "facts": {
      "aspirin for mi prophylaxis": {
        "present": true,
        "value": null,
        "days_ago": null,
        "current": true
      }
    }
  },
  "gold": true,
  "group": "ASP-FOR-MI",
  "depth": null
}
```

Criterion:

```json
{
  "schema_version": "0.1.0",
  "criterion_id": "n2c2:ASP-FOR-MI",
  "source": "n2c2_2018",
  "polarity": "inclusion",
  "text": "Use of aspirin to prevent myocardial infarction.",
  "expression": {
    "node_type": "atom",
    "entity": {
      "text": "aspirin for mi prophylaxis",
      "type": "drug",
      "codes": {}
    },
    "temporal": {
      "operator": "current",
      "value": null,
      "unit": null,
      "anchor": "enrollment"
    },
    "numeric": null
  },
  "metadata": {
    "tag": "ASP-FOR-MI"
  }
}
```

**Verdict (A / B / C):** 

**Reasoning:** 

---

## `match:ASP-FOR-MI:006`  (gold: **not_met**)

```json
{
  "item_id": "match:ASP-FOR-MI:006",
  "task": "matching",
  "criterion": {
    "schema_version": "0.1.0",
    "criterion_id": "n2c2:ASP-FOR-MI",
    "source": "n2c2_2018",
    "polarity": "inclusion",
    "text": "Use of aspirin to prevent myocardial infarction.",
    "expression": {
      "node_type": "atom",
      "entity": {
        "text": "aspirin for mi prophylaxis",
        "type": "drug",
        "codes": {}
      },
      "temporal": {
        "operator": "current",
        "value": null,
        "unit": null,
        "anchor": "enrollment"
      },
      "numeric": null
    },
    "metadata": {
      "tag": "ASP-FOR-MI"
    }
  },
  "facts": {
    "record_id": "ASP-FOR-MI-P006",
    "facts": {
      "aspirin for mi prophylaxis": {
        "present": true,
        "value": null,
        "days_ago": null,
        "current": false
      }
    }
  },
  "gold": false,
  "group": "ASP-FOR-MI",
  "depth": null
}
```

Criterion:

```json
{
  "schema_version": "0.1.0",
  "criterion_id": "n2c2:ASP-FOR-MI",
  "source": "n2c2_2018",
  "polarity": "inclusion",
  "text": "Use of aspirin to prevent myocardial infarction.",
  "expression": {
    "node_type": "atom",
    "entity": {
      "text": "aspirin for mi prophylaxis",
      "type": "drug",
      "codes": {}
    },
    "temporal": {
      "operator": "current",
      "value": null,
      "unit": null,
      "anchor": "enrollment"
    },
    "numeric": null
  },
  "metadata": {
    "tag": "ASP-FOR-MI"
  }
}
```

**Verdict (A / B / C):** 

**Reasoning:** 

---

## `match:ASP-FOR-MI:007`  (gold: **met**)

```json
{
  "item_id": "match:ASP-FOR-MI:007",
  "task": "matching",
  "criterion": {
    "schema_version": "0.1.0",
    "criterion_id": "n2c2:ASP-FOR-MI",
    "source": "n2c2_2018",
    "polarity": "inclusion",
    "text": "Use of aspirin to prevent myocardial infarction.",
    "expression": {
      "node_type": "atom",
      "entity": {
        "text": "aspirin for mi prophylaxis",
        "type": "drug",
        "codes": {}
      },
      "temporal": {
        "operator": "current",
        "value": null,
        "unit": null,
        "anchor": "enrollment"
      },
      "numeric": null
    },
    "metadata": {
      "tag": "ASP-FOR-MI"
    }
  },
  "facts": {
    "record_id": "ASP-FOR-MI-P007",
    "facts": {
      "aspirin for mi prophylaxis": {
        "present": true,
        "value": null,
        "days_ago": null,
        "current": true
      }
    }
  },
  "gold": true,
  "group": "ASP-FOR-MI",
  "depth": null
}
```

Criterion:

```json
{
  "schema_version": "0.1.0",
  "criterion_id": "n2c2:ASP-FOR-MI",
  "source": "n2c2_2018",
  "polarity": "inclusion",
  "text": "Use of aspirin to prevent myocardial infarction.",
  "expression": {
    "node_type": "atom",
    "entity": {
      "text": "aspirin for mi prophylaxis",
      "type": "drug",
      "codes": {}
    },
    "temporal": {
      "operator": "current",
      "value": null,
      "unit": null,
      "anchor": "enrollment"
    },
    "numeric": null
  },
  "metadata": {
    "tag": "ASP-FOR-MI"
  }
}
```

**Verdict (A / B / C):** 

**Reasoning:** 

---
