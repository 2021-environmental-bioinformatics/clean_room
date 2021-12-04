# clean_room

# Methods: A Reproducibility Analysis of 'A comprehensive metagenomics framework to characterize organisms relevant for planetary protection'
#### Annaliese Meyer and Matt Baldes

This document describes the steps taken to process a subset of samples from Danko et al. (2021) and our attempts to recreate the figures from their manuscript. 

## General Notes
The cap2 pipeline was only used for the first preprocessing step, all other packages were downloaded and run individually.
Parameters for these steps were taken, when present, from the source code for the cap2 pipeline (https://github.com/MetaSUB/CAP2/tree/master/cap2/pipeline).

## Preprocessing 
Generate adapter free reads, use first step of established cap2 pipeline. First and only use of pipeline.
Run "prepro.qsub"
  Stage: "pre"; Config: "config.yaml"; Manifest: "ISO5.txt", "ISO68.txt"
Output Adapter Free Reads to "output/adapter_removal"

Remove human reads for each sample
Run "bowtie2_human.qsub"
  Human genome: hg38.fa.gz (wget "https://hgdownload.cse.ucsc.edu/goldenpath/hg38/bigZips/hg38.fa.gz")
  --un-conc-gz
  --very-sensitive
Output Human Free Reads to "output/bowtie2/human"

Error correct human free reads for each sample 
Run "error_correction.qsub"
  First step of MetaSPAdes pipeline (--only-error-correction)
  --meta
Output Error Corrected Reads to "output/error_corrected"

## Kmer Counts
To count kmers for each sample, use Jellyfish v0.8.9. First, activate the `jellyfish.yml` file, located in `cleanroom/envs`. Then, run `jellyfish.qsub` with the input argument `samplelist`, which will output a binary file for each sample through the `jellyfish count` command. Flags: -m (31 or 15) -s 100M -t 8 -o 'mercounts(31 or 15).jf'

To process the binary files, use `jellydump.sh` with `samplelist`, which will run the `jellyfish dump` command. Flags: defaults, -o counts(31 or 15).fa

Then, to count singletons and total kmers, use the `jellycounts.sh` script with `samplelist`. This will output a text file that lists the sample name, the kmer length used, then the singleton count and the total kmer count.  

Script: 
```
for i in $(cat ${1})
do
  echo $i
  cd $i
  echo '15'
  wc -l counts15.fa
  grep -o 1 counts15.fa | wc -l 
  echo '31'
  wc -l counts31.fa
  grep -o 1 counts15.fa | wc -l
  cd ..
done
```


## Taxonomic Classification

## Assembly
Assmeble genomes for each sample  
Run "assembly.qsub"
  MetaSPAdes pipeline (--only-assembler)
  -m 200
Output Contigs to "output/assembly"

Binning
Run "metabat2.qsub"
  Some processing is necessary before running metabat2 (runMetaBat.sh)
    Each sample is first indexed with bwa index to prepare contigs file for bwa mem
      -a bwtsw (for large files)
    Use bwa mem to generate a .sam file for each sample
    Use samtools sort to generate a .bam file from the .sam file for each sample 
      -O bam (specifies bam output)
      -@ (# of threads)
  Run metabat2 for each sample (runMetaBat.sh)
    -m 1500
    --maxP 95
    --minS 60
    --maxEdges 200
    --pTNF 0
    --seed 10
    --saveCls
All output to "output/metabat2"
Final bins locates in "output/metabat2/ISO5/bins" and "output/metabat2/ISO6-8/bins"

Quality Control
Run "checkm.qsub"
      
