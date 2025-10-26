from scipy import stats
import pandas as pd
import numpy as np


def pivot_measures(row: pd.Series) -> pd.DataFrame:
    """
    Pivot a Series corresponding to measurements from a calibration report,
    into a table with fiducial marker x,y and angle values.

    :param row: the Series object to pivot
    :returns: the pivoted DataFrame with columns x, y, and angle
    """
    fid_names = [f"P{nn}" for nn in range(1, 9)]
    col_names = ['ll', 'ur', 'ul', 'lr', 'ml', 'mr', 'mt', 'mb']

    x_vals = [getattr(row, f"{cc}x") for cc in col_names]
    y_vals = [getattr(row, f"{cc}y") for cc in col_names]

    pivoted = pd.DataFrame(data={'name': fid_names, 'x': x_vals, 'y': y_vals})
    pivoted['angle'] = pivoted.apply(compute_angle, axis=1)

    return pivoted


def compute_angle(row: pd.Series) -> float:
    """
    Calculae the angle of a fiducial marker using the x, y values in a Series.

    :param row: the Series with x, y values corresponding to the marker x, y location
    :returns: the angle computed using numpy.arctan2
    """
    return np.arctan2(row.y, row.x)


def compute_statistics(info: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, int, int]:
    """
    Compute statistics for both the fiducial marker separation and location (if provided),
    using a DataFrame where each row corresponds to calibration report information.

    :paran info: the DataFrame to compute the statistics for
    :returns:
        - **dists** - a DataFrame with the mean (± std. dev) and median marker separation for each
          pair of fiducial markers
        - **fids** - a DataFrame with the mean (± std. dev) x,y position and mean angle for each
          fiducial marker (if at least one set of marker locations is available)
        - **nrep_dists** - the number of unique reports used for the marker separations
        - **nrep_fids** - the number of unique reports used for the marker locations

    """
    # want: angle mean, angle std. dev, mean x, mean y for each fiducial marker
    # diagonal, straight marker separation (mean ± std, median)
    dists = pd.DataFrame()

    nrep_dists = len(info)

    for meas in ['lr_dist', 'tb_dist', 'llur_dist', 'ullr_dist']:
        if np.count_nonzero(~info[meas].isna()) > 0:
            dists.loc[meas, 'mean'] = f"{info[meas].mean():.3f} ± {info[meas].std():.3f}"
            dists.loc[meas, 'median'] = f"{info[meas].median():.3f}"

    dists = dists.reset_index(names='markers').replace(
        {'lr_dist': 'P5 - P6', 'tb_dist': 'P7 - P8', 'llur_dist': 'P1 - P2', 'ullr_dist': 'P3 - P4'}
    ).set_index('markers')

    pivoted = pd.concat(
        [pivot_measures(row) for row in info.itertuples()],
        ignore_index=True
    ).dropna(subset=['x', 'y'], how='all')

    if len(pivoted) > 0:
        grouped = pivoted.groupby('name')
        nrep_fids = int(grouped['x'].count().median())
        xmean = grouped['x'].mean()
        xmean -= xmean.min()

        ymean = grouped['y'].mean()
        ymean = -ymean - (-ymean).min()

        std_x = grouped['x'].std()
        std_y = grouped['y'].std()

        fids = pd.DataFrame()
        fids['x'] = xmean.apply(lambda s: f"{s:.3f}") + ' ± ' + std_x.apply(lambda s: f"{s:.3f}")
        fids['y'] = ymean.apply(lambda s: f"{s:.3f}") + ' ± ' + std_y.apply(lambda s: f"{s:.3f}")

        fids['angle'] = (np.rad2deg(grouped['angle'].apply(stats.circmean)) % 360).apply(lambda s: f"{s:.3f}")
    else:
        fids = None
        nrep_fids = 0

    return dists, fids, nrep_dists, nrep_fids


def nice_table(info: pd.DataFrame) -> None:
    """
    Print markdown-formatted tables for the fiducial marker separation and location statistics.

    :paran info: the DataFrame to compute the statistics for
    """
    dists, fids, nrep_dists, nrep_fids = compute_statistics(info)

    outstr = f"**Marker Separation (n = {nrep_dists} reports)**\n\n" + dists.to_markdown(tablefmt='grid')

    if fids is not None:
        outstr += f"\n\n**Marker Location (n = {nrep_fids} reports)**\n\n" + fids.to_markdown(tablefmt='grid')

    print(outstr.replace(':', '-'))
