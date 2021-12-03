# clean_room

# General Notes
The cap2 pipeline was only used for the first preprocessing step, all other packages were downloaded and run individually.
Parameters for these steps were taken, when present, from the source code for the cap2 pipeline (https://github.com/MetaSUB/CAP2/tree/master/cap2/pipeline)

# Preprocessing 
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

# Assembly
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
      
