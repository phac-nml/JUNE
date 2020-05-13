import logging
import os
from itertools import chain
from enum import IntEnum
from pathlib import Path
from typing import List, Dict, Optional

import numpy as np
import pandas as pd
from scipy.stats import rv_discrete

from june.geography import Geography, SuperArea
from june.groups.group import Group, Supergroup

default_data_path = (
    Path(os.path.abspath(__file__)).parent.parent.parent
    / "data/processed/census_data/company_data/"
)
default_size_nr_file = default_data_path / "companysize_msoa11cd_2019.csv"
default_sector_nr_per_msoa_file = default_data_path / "companysector_msoa11cd_2011.csv"
default_areas_map_path = (
    Path(os.path.abspath(__file__)).parent.parent.parent
    / "data/processed/geographical_data/oa_msoa_region.csv"
)

logger = logging.getLogger(__name__)


class CompanyError(BaseException):
    pass


class Company(Group):
    """
    The Company class represents a company that contains information about 
    its workers which are not yet distributed to key company sectors
    (e.g. as schools and hospitals).

    Currently we treat the workforce of a company as one single sub-group
    and therefore we invoke the base class group with the default Ngroups = 1.
    We made this explicit here, although it is not necessary.
    """

    __slots__ = (
        "super_area",
        "industry",
        "n_employees_max",
    )

    class GroupType(IntEnum):
        workers = 0

    def __init__(self, super_area=None, n_workers_max=np.inf, sector=None):
        super().__init__()
        self.super_area = super_area
        self.sector = sector
        self.n_workers_max = n_workers_max

    @property
    def n_workers(self):
        return len(self.people)

class Companies(Supergroup):
    def __init__(self, companies: List["Companies"]):
        """
        Create companies and provide functionality to allocate workers.

        Parameters
        ----------
        company_size_per_superarea_df: pd.DataFram
            Nr. of companies within a size-range per SuperArea.

        compsec_per_msoa_df: pd.DataFrame
            Nr. of companies per industry sector per SuperArea.
        """
        super().__init__()
        self.members = companies

    @classmethod
    def for_geography(
        cls,
        geography: Geography,
        size_nr_file: str = default_size_nr_file,
        sector_nr_per_msoa_file: str = default_sector_nr_per_msoa_file,
    ) -> "Companies":
        """
        Creates companies for the specified geography, and saves them 
        to the super_aresa they belong to
        Parameters
        ----------
        geography
            an instance of the geography class
        company_size_per_superarea_filename: 
            Nr. of companies within a size-range per SuperArea.
        compsec_per_msoa_filename: 
            Nr. of companies per industry sector per SuperArea.
        """
        if len(geography.super_areas) == 0:
            raise CompanyError("Empty geography!")
        return cls.for_super_areas(
            geography.super_areas, size_nr_file, sector_nr_per_msoa_file
        )

    @classmethod
    def for_super_areas(
        cls,
        super_areas: List[SuperArea],
        size_nr_per_super_area_file: str = default_size_nr_file,
        sector_nr_per_super_area_file: str = default_sector_nr_per_msoa_file,
    ) -> "Companies":
        """Creates companies for the specified super_areas, and saves them 
        to the super_aresa they belong to
        Parameters
        ----------
        super_areas
            list of super areas
        company_size_per_superarea_filename: 
            Nr. of companies within a size-range per SuperArea.
        compsec_per_msoa_filename: 
            Nr. of companies per industry sector per SuperArea.

        Parameters
        ----------
        """
        size_per_superarea_df = pd.read_csv(size_nr_per_super_area_file, index_col=0)
        sector_per_superarea_df = pd.read_csv(
            sector_nr_per_super_area_file, index_col=0
        )
        super_area_names = [super_area.name for super_area in super_areas]
        company_sizes_per_super_area = size_per_superarea_df.loc[super_area_names]
        company_sectors_per_super_area = sector_per_superarea_df.loc[super_area_names]
        if len(company_sectors_per_super_area) == 1:
            companies = cls.create_companies_in_super_area(
                super_areas[0],
                company_sizes_per_super_area,
                company_sectors_per_super_area,
            )
        else:
            companies = chain(
                *list(
                    map(
                        cls.create_companies_in_super_area,
                        super_areas,
                        company_sizes_per_super_area,
                        company_sectors_per_super_area,
                    )
                )
            )
        np.random.shuffle(companies)
        return cls(companies)

    @classmethod
    def create_companies_in_super_area(cls, super_area, company_sizes, company_sectors):
        sizes = []
        for size_bracket, counts in company_sizes.items():
            size_min, size_max = _get_size_brackets(size_bracket)
            sizes += list(np.random.randint(max(size_min,1), size_max, int(counts.values[0])))
        sectors = []
        for sector, counts in company_sectors.items():
            sectors += [sector] * int(counts)
        np.random.shuffle(sectors)
        companies = list(
            map(
                lambda company_size, company_sector: cls.create_company(
                    super_area, company_size, company_sector
                ),
                sizes,
                sectors,
            )
        )
        return companies

    @classmethod
    def create_company(cls, super_area, company_size, company_sector):
        company = Company(super_area, company_size, company_sector)
        return company


def _get_size_brackets(sizegroup: str):
    """
    Given company size group calculates mean
    """
    # ensure that read_companysize_census() also returns number of companies
    # in each size category
    size_min, size_max = sizegroup.split("-")
    if size_max == "XXX" or size_max == "xxx":
        size_min = int(size_min)
        size_max = 1500
    else:
        size_min = int(size_min)
        size_max = int(size_max)
    return size_min, size_max
