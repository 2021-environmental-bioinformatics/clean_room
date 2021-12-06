# clean_room

# Methods: A Reproducibility Analysis of 'A comprehensive metagenomics framework to characterize organisms relevant for planetary protection'
#### Annaliese Meyer and Matt Baldes

This document describes the steps taken to process a subset of samples from Danko et al. (2021) and our attempts to recreate the figures from their manuscript. 

## General Notes
The CAP2 pipeline was only used for the first preprocessing step, all other packages were downloaded and run individually.
Parameters for these steps were taken, when present, from the source code for the CAP2 pipeline (https://github.com/MetaSUB/CAP2/tree/master/cap2/pipeline).

## File Structure
<img width="710" alt="Screenshot 2021-12-04 at 3 08 12 PM" src="https://user-images.githubusercontent.com/47222962/144723204-60a42cb9-aa56-4e91-8f82-578cf769b099.png">
The above image shows the top file structure of our repository. We will describe the contents of each folder below. 

`analysis`: contains singleton counts file

`code`: contains various GitHub repositories used to build programs investigated in the course of this project

`config`: contains configuration files for the CAP2 pipeline

`databases`: contains databases for the CAP2 pipeline

`envs`: contains environments needed to execute the below commands. Please see documentation for which environemnt to use at which point. 

`jupyter-notebooks`: contains final report and jupyter notebooks used for figure creation and analysis

`logs`: contains logs from script runs throughout the course of the project

`output`: 

<img width="657" alt="Screenshot 2021-12-04 at 3 20 07 PM" src="https://user-images.githubusercontent.com/47222962/144723511-72266f75-4e23-457c-b5d2-bddd4733495b.png">

Output contains folders for the output of each program. For short reads analysis and raw data, each sample has its own labeled folder within the program folder containing its specific output.

`pangea-api`: program necessaryto download data from Pangea

`raw_data`: contains raw data downloaded from Pangea

`scripts`: contains  `goodscripts` i.e. scripts used for the final pipeline, and `testscripts`, i.e. those used in experimentation or for programs not used


## Preprocessing 
To generate adapter free reads, use the first step of the established CAP2 pipeline. This will be the first and only use of this pipeline. First, activate `CAP2.yml`, located in `cleanroom/envs`. Then run `prepro.qsub`. This activates the pipeline using `cap2` and specifies the preprocessing stage (pre). `cap2` takes a config file: `config.yaml` and a manifest file: `ISO5.txt`, `ISO68.txt`. These files are located in `raw_data` with the raw samples. The script `prepro.qsub` will output adapter free reads to `output/adapter_removal`.

The next step is to remove human contamination from each sample. To do this, first activate the `bowtie2.yml` conda environment. It is necessary to download the human genome before running `bowtie2`. The human genome (hg38) can be downloaded from UCSC with the following command:
```
wget "https://hgdownload.cse.ucsc.edu/goldenpath/hg38/bigZips/hg38.fa.gz"
```
Download hg38 to `raw_data`. This should yield the file `hg38.fa.gz`.

Now run `bowtie2_human.qsub`. This script first indexes hg38 with `bowtie2 build` then runs `bowtie2` with the flags  --un-conc-gz and --very-sensitive
    
`bowtie2_human.qsub` outputs human free reads to `output/bowtie2/human`

The final preprocessing step is to error correct the human free reads for each sample. Activate `metaspades.yml`. The script `error_correction.qsub` uses the irst step of `MetaSPAdes` pipeline (--only-error-correction) with the --meta flag to output error corrected reads to `output/error_corrected`.

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
For taxonomic classification, first activate the conda environment `kraken2.yml`, then use the `kraken2` script with `samplelist` as the input argument. Flags: --db /vortexfs1/omics/env-bio/collaboration/databases/kraken2db_pluspf --threads 8 --output output_default --report report_default.kreport --paired

To convert the kraken2 single outputs for each sample type, activate `kraken2-biom.yml`, use `rename-for-biom` with `samplelist`. The script will adjust file names and locations. The output will be a file called `cleanroom.biom`. Flags: default

## Assembly
Assmebling the genomes for each sample will again require the `MetaSPAdes` pipeline, so activate `metaspades.yaml` once more. Next run `assembly.qsub` with the flags --only-assembler and -m 200. This script takes in human free, error corrected, reads and will output contigs to `output/assembly`.

## Binning
To generate bins from the geberated contigs for each sample, activate `metabat2.yml` and run `metabat2.qsub`. Some processing is included in this script before running `metabat2` (`runMetaBat.sh`). Each sample is first indexed with `bwa index` to prepare the contigs file for `bwa mem` flags: -a bwtsw (for large files). Next,  `bwa mem` is used to generate a .sam file for each sample and `samtools sort` is used to generate a .bam file from each .sam file. `samtools sort` flags: -O bam (specifies bam output) -@ (# of threads). -@ is often expressed as -t, --threads, or --cpus in other packages. 
  
Finally, the script runs `metabat2` for each sample (`runMetaBat.sh`) with the following flags: -m 1500, --maxP 95, --minS 60, --maxEdges 200, --pTNF 0, --seed 10, and --saveCls. All output for this script goes to `output/metabat2` and the final bins are located in `output/metabat2/ISO5/bins` and `output/metabat2/ISO6-8/bins`.

## Quality Control
To ensure that the generate bins are up to standard, use `checkm` to generate quality statistics. First, activate `checkm.yml` and run `checkm.qsub`. `checkm` flags: --pplacer_threads 2 and -x fa. This script will output to `output/CheckM/ISO5` and `output/CheckM/ISO6-8`.

For this project, only bins with >80% completeness nd <5% contamination were accepted for further analysis. Some processing is required to find these quality bins. The following commands are useful for refining the stats table generated by `checkm` to show quality bins:

```
#Trim the initial file bin_stats_ext.tsv to show only the bin name, completeness, and contamination:

awk -F ',' -v OFS='\t' '{print substr($1, 1, 6), $11, $12}' bin_stats_ext.tsv for file in *; do echo ${file} >> bin_stats.txt; awk -F ',' -v OFS='\t' '{print substr($1, 1, 6), $11, $12}' ${file}/storage/bin_stats_ext.tsv >> bin_stats.txt; done

#Trim bin_stats.txt further for ease of viewing:

awk -F ' ' -v OFS='\t' '{print $1, $3, $5}' bin_stats.txt > bin_stat_short.txt

#Finally search bin_stat_short.txt using grep for completeness values over 80:

grep -e "8.\." -e "9.\." -e "_" bin_stat_short.txt > bin_stats_complete.txt

#Values in bin_stats_complete.txt with contamination less than 5 are quality bins
```

## Classification
`GTDB-Tk` can be used to classify quality bins. To do this, activate `gtdbtk.yml` and run `gtdbtk.qsub`. `gtdbtk classify_wf` flags: --extension fa. This script outputs to `output/gtdbtk`. The taxonomic id for each bin can be found in `gtdbtk.bac120.summary.tsv` for each sample. This information can be used to rename bins and feed them back into `GTDB-Tk`. To do this run `gtdbtk_2.qsub` on renamed files. A second run in this way is useful to generate an aligned file `gtdbtk.bac120.user_msa.fasta` that can be used as input to generate a treefile with `iqtree`:
```
iqtree -s gtdbtk.bac120.user_msa.fasta -nt 8 -redo -m TEST
```
To run this command, first activate the conda environment `iqtree.yml`.

## Annotation
Activate `prokka.yml` and run `prokka.qsub` to annotate bins with proteins. Output for this script can be found at `output/prokka`. These proteins can be further explored in reference to their relevance to extremophilic traits with information from the Microbe Directory, which provides groups of proteins associated with different traits (https://github.com/dcdanko/MD2/tree/master/protein_groups). For example, running the following command on `prokka` output files can identify which taxa have proteins associated with biocide resistance:
```
for file in *; do echo ${file} >> biocideResistance.txt; grep -f /vortexfs1/omics/env-bio/collaboration/clean_room/output/prokka/biocideResistanceProts.txt ${file}/${file}.tsv >> biocideResistance.txt; done
```
      
