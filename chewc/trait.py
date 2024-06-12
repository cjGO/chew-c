# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/02_trait.ipynb.

# %% auto 0
__all__ = ['select_qtl_loci', 'TraitModule']

# %% ../nbs/02_trait.ipynb 4
from .core import *
import torch
import attr
from typing import Tuple, Optional, List, Union
from fastcore.test import *
import matplotlib.pyplot as plt
import torch.nn as nn
import pdb


def select_qtl_loci(num_qtl_per_chromosome: int, genome: Genome) -> torch.Tensor:
    """
    Randomly selects loci to be QTLs on each chromosome.

    Args:
        num_qtl_per_chromosome (int): Number of QTLs to select per chromosome.
        genome (Genome): Genome object containing the chromosome structure.

    Returns:
        torch.Tensor: A boolean tensor indicating which loci are QTLs. 
                      Shape: (number_chromosomes, loci_per_chromosome)
    """
    
    assert num_qtl_per_chromosome <= genome.n_loci_per_chromosome, "Too many QTLs for this trait given your Genome object"
    assert num_qtl_per_chromosome > 0, "You need at least 1 QTL per chromosome"
    
    qtl_indices = []
    for _ in range(genome.n_chromosomes):
        chromosome_indices = torch.randperm(genome.n_loci_per_chromosome)[:num_qtl_per_chromosome]
        chromosome_qtl_flags = torch.zeros(genome.n_loci_per_chromosome, dtype=torch.bool)
        chromosome_qtl_flags[chromosome_indices] = True
        qtl_indices.append(chromosome_qtl_flags)
    
    return torch.stack(qtl_indices).to(genome.device)



class TraitModule(nn.Module):
    """
    Module for managing and simulating multiple correlated additive traits.
    """
    def __init__(self, genome: Genome,founder_pop, target_means: torch.Tensor, target_vars: torch.Tensor, 
                 correlation_matrix: torch.Tensor, n_qtl_per_chromosome: int):
        """
        Initializes the TraitModule.

        Args:
            genome (Genome): The genome object.
            target_means (torch.Tensor): Target means for each trait (n_traits).
            target_vars (torch.Tensor): Target variances for each trait (n_traits).
            correlation_matrix (torch.Tensor): Correlation matrix between traits (n_traits, n_traits).
            n_qtl_per_chromosome (int): Number of QTLs per chromosome for each trait.
        """
        super().__init__()
        self.genome = genome
        self.founder_pop = founder_pop
        self.n_traits = len(target_means)
        self.target_means = target_means.to(genome.device)
        self.target_vars = target_vars.to(genome.device)
        self.correlation_matrix = correlation_matrix.to(genome.device)
        self.n_qtl_per_chromosome = n_qtl_per_chromosome
        
        self.qtl_loci = select_qtl_loci(n_qtl_per_chromosome, genome)
        self.effects = self._initialize_correlated_effects()
        self.intercepts = self._calculate_intercepts()
        

    def _initialize_correlated_effects(self) -> torch.Tensor:
        """
        Samples and scales correlated additive effects for all traits.

        Returns:
            torch.Tensor: Correlated effects (n_chromosomes, n_loci_per_chromosome, n_traits).
        """
        n_chr, n_loci = self.genome.genetic_map.shape
        
        L = torch.linalg.cholesky(self.correlation_matrix)

        uncorrelated_effects = torch.randn(n_chr, n_loci, self.n_traits, device=self.genome.device)
        uncorrelated_effects = uncorrelated_effects.reshape(n_chr * n_loci, self.n_traits)

        correlated_effects = torch.matmul(L, uncorrelated_effects.T).T
        return correlated_effects.reshape(n_chr, n_loci, self.n_traits)

    def _calculate_intercepts(self) -> torch.Tensor:
        """
        Calculates intercepts for each trait to achieve the target means.
        
        Note:
            This calculation depends on an initial population to get unscaled means and variances.
            You should call this method after creating a founder population.

        Returns:
            torch.Tensor: Trait intercepts (n_traits).
        """
        # Example: Calculate intercepts based on a founder population
        dosages = self.founder_pop.get_dosages()
        unscaled_bvs = self.calculate_breeding_values(dosages, scale_effects=False)
        unscaled_var = unscaled_bvs.var(dim=0, unbiased=False)
        unscaled_mean = unscaled_bvs.mean(dim=0)
        
        scaling_factors = torch.sqrt(self.target_vars / unscaled_var)
#         import pdb; pdb.set_trace()
        self.effects *= scaling_factors.view(1, 1, 3)  # Scale the effects
        return self.target_means - (unscaled_mean * scaling_factors)

    def calculate_breeding_values(self, dosages: torch.Tensor, scale_effects: bool = True) -> torch.Tensor:
        """
        Calculates breeding values for all traits given allele dosages.

        Args:
            dosages (torch.Tensor): Allele dosages (population_size, n_chromosomes, n_loci_per_chromosome).
            scale_effects (bool): Whether to scale effects to target variances. Defaults to True.

        Returns:
            torch.Tensor: Breeding values for all traits (population_size, n_traits).
        """
        if scale_effects:
            return torch.einsum('ijk,jkl->il', dosages.float(), self.effects) + self.intercepts 
        else:
            return torch.einsum('ijk,jkl->il', dosages.float(), self.effects)
    
    def forward(self, dosages: torch.Tensor, h2: Optional[Union[float, torch.Tensor]] = None, 
                varE: Optional[Union[float, torch.Tensor]] = None) -> torch.Tensor:
        """
        Calculates breeding values and adds environmental noise.

        Args:
            dosages (torch.Tensor): Allele dosages (pop_size, n_chr, n_loci).
            h2 (Optional[Union[float, torch.Tensor]]): Heritability (single value or per trait). 
            varE (Optional[Union[float, torch.Tensor]]): Environmental variance (single value or per trait).

        Returns:
            torch.Tensor: Phenotypes (pop_size, n_traits).
        """
        breeding_values = self.calculate_breeding_values(dosages.float())
        
        # Add environmental noise
        if varE is not None:
            if isinstance(varE, float):
                varE = torch.tensor([varE] * self.n_traits, device=self.genome.device)
            env_noise = torch.randn_like(breeding_values) * torch.sqrt(varE)
            return breeding_values + env_noise 
        elif h2 is not None:
            if isinstance(h2, float):
                h2 = torch.tensor([h2] * self.n_traits, device=self.genome.device)
            varG = breeding_values.var(dim=0, unbiased=False)
            varE = varG * (1 - h2) / h2
            env_noise = torch.randn_like(breeding_values) * torch.sqrt(varE)
            return breeding_values + env_noise
        else:
            return breeding_values  # No noise added
