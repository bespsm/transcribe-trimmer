# TRANSCRIBE-TRIMMER

*SST output cleaning algorithm.* It fixes misstakes/typos of a SST model result with availability of the original speech transcription.

## EXAMPLES

In `examples/` folder you can compare `chunks_in.txt` with algorithm result `chunks_out.txt`. `check_text.txt` was used as original text.

## UASGE

Run:
```
python3 transcribe-trimmer/__main__.py -c transcribe-trimmer/config.yaml
```

*config.yaml* is a file that contains algorthm settings. Parameters description:

* config.yaml:path:in_text - path to input dataset file
* config.yaml:path:check_text - path to original text file
* config.yaml:path:out_text - path to output file
* config.yaml:chars:chunk_separator - character that will be treated as separator between text phrases
* config.yaml:chars:strip - list of characters to be striped in *out_text*
* config.yaml:chars:space_replace - list of characters that will be replaced with space sign
* config.yaml:algorithm:small_phrase_size - min number of characters in the phrase that triggers different searching algorithm 
* config.yaml:algorithm:words_ahead_to_check - for how many words ahead to look for a similar phrase in original text
* config.yaml:algorithm:words_behind_to_check - for how many words behind to look for a similar phrase in original text
* config.yaml:algorithm:mistakes_border - number of characters in one phrase that 
