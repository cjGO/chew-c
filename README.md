# Chew-C


<!-- WARNING: THIS FILE WAS AUTOGENERATED! DO NOT EDIT! -->

``` python
from burbankai.core import *
```

In short, this will be a GPU-enabled stochastic simulation for breeding
programs with an emphasis on cost-benefit-analysis for novel breeding
tools and creating a suitable interface for RL agents.

------------------------------------------------------------------------

We will also incorporate an emphasis on budget and costs associated with
each action to manage long-term breeding budgets. As well as model
theoretical tools in the plant breeder’s toolbox. e.g.

> a treatment which increases crossover rates

> a treatment which reduces flowering time

> a treatment which enables gene drive at select loci

Each treatment will cost \$\$ ultimately helping guide the
implementation in real-world breeding programs.

## Install

``` sh
pip install chew-c
```

## How to use

First, define the genome of your crop

``` python
ploidy = 2
number_chromosomes = 10
loci_per_chromosome = 100
n_founders = 50
genetic_map = create_uniform_genetic_map(number_chromosomes,loci_per_chromosome)
crop_genome = Genome(ploidy, number_chromosomes, loci_per_chromosome, genetic_map)
founder_pop = create_random_founder_pop(crop_genome , n_founders)


qtl_map = select_qtl_loci(20, crop_genome)
marker_fx = generate_marker_effects(qtl_map)

founder_genetic_variance = calculate_genetic_variance(founder_pop,marker_fx,crop_genome)
scaled_marker_fx = scale_marker_effects(marker_fx, founder_genetic_variance, 0.5)
```
