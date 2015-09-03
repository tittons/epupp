#!/usr/local/bin/python3

from modules.epupp import EpuPP

if __name__ == "__main__": 
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-i','--input', help='Input file name',required=True)
    parser.add_argument('-o','--output',help='Output file name', required=True)
    args = parser.parse_args()
    if args.input and args.output:
        res = EpuPP(args.input, args.output)
        print(res.write_to_file(res.get_chapters()))
        print(res.extract_images())
        print(res.write_to_file(res.get_epub_info(), "epub_info.json"))
        print(res.write_to_file(res.get_chapters_list(), "chapters_list.json"))