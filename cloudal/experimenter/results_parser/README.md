# How it works
The architecture of the parser presented in the following diagram:
<p align="center">
    <br>
    <img src="https://raw.githubusercontent.com/ntlinh16/cloudal/master/images/cloudal_parser.png" width="650"/>
    <br>
<p>

# How to use

You may want to use `-h` to see all the options:
```
$ python result_parser.py -h
usage: parse_result [-h] -i INPUT -o OUTPUT -p
                    {fmke_pop,elmerfs_bench,elmerfs_copy,elmerfs_convergence,fmke_client}
                    [{fmke_pop,elmerfs_bench,elmerfs_copy,elmerfs_convergence,fmke_client} ...]
                    [-f {csv,xlsx}]

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        The path to the result directory.
  -o OUTPUT, --output OUTPUT
                        The path to the output result file.
  -p {fmke_pop,elmerfs_bench,elmerfs_copy,elmerfs_convergence,fmke_client} [{fmke_pop,elmerfs_bench,elmerfs_copy,elmerfs_convergence,fmke_client} ...]
                        Parser to use
  -f {csv,xlsx}         Output format
```
# How to add more parser

You can write your own parser in `parsers` directory.