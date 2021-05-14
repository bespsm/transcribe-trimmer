#!/usr/bin/env python3
# MIT License
# Copyright (c) 2021 Sergey B <dkc.sergey.88@hotmail.com>

from logging import log, INFO, ERROR, basicConfig
import argparse
import jellyfish
import os
import yaml
import re


class transcribe_chunk:
    def __init__(self, chunk_id, dirty_transcript):
        self.chunk_id = chunk_id
        self.transcript = dirty_transcript
        self.transcript_len = len(dirty_transcript)
        self.is_start_iter_match = False
        self.is_end_iter_match = False
        self.is_found = False
        self.iter_pos_start = -1
        self.iter_pos_end = -1


class phrase_comparator:
    def __init__(self, mistakes_border, small_phrase_border):
        self.analyze_dict = {}
        self.mistakes_border = mistakes_border
        self.small_mistake_border = mistakes_border - 0.07
        self.small_phrase_border = small_phrase_border
        self.last_result = None

    def compare_two_phrases(self, f_phrase, s_phrase, compare_from_end=False):

        f_concat_phrase = "".join(f_phrase)
        s_concat_phrase = "".join(s_phrase)
        f_compare = ""
        s_compare = ""

        if len(f_concat_phrase) < self.small_phrase_border:
            # comprare words
            if not compare_from_end:
                f_compare = f_concat_phrase[:len(f_concat_phrase)]
                s_compare = s_concat_phrase[:len(f_concat_phrase)]
            else:
                f_compare = f_concat_phrase[-len(f_concat_phrase):]
                s_compare = s_concat_phrase[-len(f_concat_phrase):]
            self.last_result = jellyfish.jaro_winkler_similarity(
                f_compare, s_compare)
        else:
            # compare concated chunks
            if not compare_from_end:
                f_compare = f_concat_phrase[:self.small_phrase_border]
                s_compare = s_concat_phrase[:self.small_phrase_border]
            else:
                f_compare = f_concat_phrase[-self.small_phrase_border:]
                s_compare = s_concat_phrase[-self.small_phrase_border:]
            self.last_result = jellyfish.jaro_winkler_similarity(
                f_compare, s_compare)

        out_res = False
        out_res = True if self.last_result > self.mistakes_border else False

        # debug line
        # print("f_compare: " + f_compare + " s_compare: " + s_compare + " res " + str(self.last_result))
        return out_res

    def store_last_result(self, el_id):
        if self.last_result > self.mistakes_border:
            self.analyze_dict[el_id] = self.last_result

    def best_result(self):
        if len(self.analyze_dict) > 0:
            max_key = max(self.analyze_dict, key=self.analyze_dict.get)
            self.analyze_dict = {}
            return True, max_key
        else:
            return False, None

    def best_results(self):
        ret_dict = None
        if len(self.analyze_dict) > 0:
            ret_dict = self.analyze_dict
            self.analyze_dict = {}
            return True, ret_dict
        else:
            return False, ret_dict


def find_full_phrase(chunk, text, text_it, small_phrase_size, words_ahead_to_check, words_behind_to_check, mistakes_border):

    dirty_phrase = chunk.transcript.split(" ")
    dirty_phrase_concat = "".join(dirty_phrase)
    phrase_size = len(dirty_phrase)
    is_small_phrase = True if len(
        dirty_phrase_concat) < small_phrase_size else False

    comp = phrase_comparator(mistakes_border, small_phrase_size)

    # try without iteration
    if comp.compare_two_phrases(dirty_phrase, text[text_it:text_it + phrase_size]):
        chunk.iter_pos_start = text_it
        chunk.is_start_iter_match = True
    else:
        if words_behind_to_check > text_it:
            start_search_area = 0
        else:
            start_search_area = text_it - words_behind_to_check
        if start_search_area + words_ahead_to_check > len(text):
            end_search_area = len(text)
        else:
            end_search_area = start_search_area + words_ahead_to_check

        for idx in range(start_search_area, end_search_area):
            comp.compare_two_phrases(dirty_phrase, text[idx:end_search_area])
            comp.store_last_result(idx)
        res, elem_id = comp.best_result()
        if res:
            chunk.iter_pos_start = elem_id

        # finish if cannot find shift iterator to have of phrase size
        if chunk.iter_pos_start == -1:
            return chunk, int(text_it + int(0.5 * phrase_size))

    # try without search
    if comp.compare_two_phrases(dirty_phrase, text[chunk.iter_pos_start:chunk.iter_pos_start + phrase_size], compare_from_end=True):
        chunk.iter_pos_end = chunk.iter_pos_start + phrase_size - 1
        chunk.is_end_iter_match = True
    else:
        if not is_small_phrase:
            if chunk.iter_pos_start + phrase_size - words_behind_to_check < 1:
                # assuming that first element is found
                start_search_area = 1
            else:
                start_search_area = chunk.iter_pos_start + \
                    int(0.5 * phrase_size)
            if chunk.iter_pos_start + int(2 * phrase_size) > len(text) + 1:
                end_search_area = len(text) + 1
            else:
                end_search_area = chunk.iter_pos_start + int(2 * phrase_size)

            for idx in range(start_search_area, end_search_area):
                comp.compare_two_phrases(
                    dirty_phrase, text[start_search_area - 1:idx], compare_from_end=True)
                comp.store_last_result(idx-1)  # real_id = id-1
            res, elem_id = comp.best_result()
            if res:
                chunk.iter_pos_end = elem_id
        else:
            chunk.iter_pos_end = chunk.iter_pos_start + phrase_size - 1

    # agregate
    if chunk.iter_pos_end != -1:
        clean_phrase = text[chunk.iter_pos_start:chunk.iter_pos_end + 1]
        chunk.transcript = list_to_str_sentence(clean_phrase)
        chunk.is_found = True
        text_it = chunk.iter_pos_end + 1
    else:
        text_it = int(text_it + phrase_size)

    return chunk, text_it


def list_to_str_sentence(sentence_list):
    sentence = ""
    for word in sentence_list:
        sentence += word + " "
    return sentence.strip()


def load_chunks(file, chunk_separator, striped_chars, space_replace):
    f = open(file, "r")
    data = f.read()
    f.close()
    data = strip_punct(data, striped_chars, space_replace)
    tr_chunks = data.split(chunk_separator)
    chunks = []
    it = 0
    for ch in tr_chunks:
        ch = ch.strip()
        chunks.append(transcribe_chunk(it, ch))
        it += 1
    return chunks


def save_chunks(path_out, chunks, separator):
    data = ""
    for chunk in chunks:
        data += chunk.transcript + separator
    f = open(path_out, "w")
    f.write(data)
    f.close()


def load_text(file, striped_chars, space_replace):
    f = open(file, "r")
    data = f.read()
    f.close()
    data = strip_punct(data, striped_chars, space_replace)
    raw_words = data.split(" ")
    return raw_words


def strip_punct(raw_text, striped_chars, space_replace):
    raw_text = raw_text.lower()
    for ch in striped_chars:
        raw_text = raw_text.replace(ch, " ")
    raw_text = re.sub(" +", " ", raw_text)
    for ch in space_replace:
        raw_text = raw_text.replace(ch, " ")
    return raw_text.strip()


def main():

    basicConfig(level=0)

    # parse input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config_path",
        help="path to config yaml file",
        type=str,
        default=os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "config.yaml"
        ),
    )
    args = parser.parse_args()

    if not os.path.exists(args.config_path):
        log(
            ERROR,
            "couldn't find file: "
            + args.config_path
        )
        return

    stream = open(args.config_path, 'r')
    conf_ya = yaml.load(stream, Loader=yaml.FullLoader)

    chunk_separator = conf_ya["chars"]["chunk_separator"]
    striped_chars = conf_ya["chars"]["strip"]
    space_replace = conf_ya["chars"]["space_replace"]

    chunks = load_chunks(conf_ya["paths"]["in_text"],
                         chunk_separator, striped_chars, space_replace)
    striped_chars.append(chunk_separator)
    text = load_text(conf_ya["paths"]["check_text"],
                     striped_chars, space_replace)

    small_phrase_size = conf_ya["algorithm"]["small_phrase_size"]
    words_ahead_to_check = conf_ya["algorithm"]["words_ahead_to_check"]
    words_behind_to_check = conf_ya["algorithm"]["words_behind_to_check"]
    mistakes_border = conf_ya["algorithm"]["mistakes_border"]

    text_it = 0
    fp_chunks = []

    for chunk in chunks:
        fp_chunk, cur_it = find_full_phrase(
            chunk, text, text_it, small_phrase_size, words_ahead_to_check, words_behind_to_check, mistakes_border)
        fp_chunks.append(fp_chunk)
        text_it = cur_it

    # counters
    total = 0
    found = 0
    is_no_iter_match = 0

    for chunk in fp_chunks:
        total += 1
        if chunk.is_found is True:
            found += 1
        if chunk.is_start_iter_match is True and chunk.is_end_iter_match is True:
            is_no_iter_match += 1

    log(INFO, "total phrases: " + str(total))
    log(INFO, "found phrases: " + str(found))
    log(INFO, "found wo iteration: " + str(is_no_iter_match))
    log(INFO, "precentage found: " + str(float(found/total) * 100))

    # save chunks
    save_chunks(conf_ya["paths"]["out_text"], fp_chunks, chunk_separator)


if __name__ == "__main__":
    main()
