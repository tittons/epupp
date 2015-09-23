#!/usr/local/bin/python3

from modules.epupp import EpuPP

if __name__ == "__main__": 
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-i','--input',help='Input file name',required=True)
    parser.add_argument('-o','--output',help='Output file name')
    parser.add_argument('-rm','--remove',help='Remove file on finish')
    args = parser.parse_args()
    with EpuPP(args.input, args.output, remove_original = args.remove if args.remove else False) as res:
        print(res.write_to_file(res.get_chapters(cleaner_params={"remove_tags":["span"]})))
        print(res.write_to_file(res.get_epub_info(), "epub_info.json"))
        print(res.write_to_file(res.get_chapters(as_list=True), "chapters_list.json"))