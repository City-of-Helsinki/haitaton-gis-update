import geopandas as gpd
import pandas as pd

def makeValid(geometry: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    geometry["geometry"] = geometry.make_valid()
    geometry["geometry"] = geometry.normalize()
    geometry.drop_duplicates()

    return geometry

def clipAreasByAreas(geometryToClip: gpd.GeoDataFrame, mask: gpd.GeoDataFrame, geometryToClipAttrsDissolve, maskAttrsDissolve, mergeIdField, geometryToClipCheckAttr=None, dissolveBetween=False) -> gpd.GeoDataFrame:
    geometry = geometryToClip[~geometryToClip.is_empty]
    for attr in maskAttrsDissolve:
        mask[attr] = mask[attr].fillna("")

    if maskAttrsDissolve:
        mask_dissolved = mask.dissolve(by=maskAttrsDissolve, as_index=False)
    else:
        mask_dissolved = mask

    mask_dissolved = mask_dissolved.explode(ignore_index=True)
    mask_dissolved = makeValid(mask_dissolved)

    if geometryToClipCheckAttr is not None:
        geometryToClipOnlyCheckObjects = geometry[geometry[geometryToClipCheckAttr].notnull()]
        geometryToClipNotCheckObjects = geometry.loc[~geometry[geometryToClipCheckAttr].notnull()]
    else:
        geometryToClipOnlyCheckObjects = geometry

    geometryToClipOnlyCheckObjects = geometryToClipOnlyCheckObjects.explode(ignore_index=True)
    geometryToClipOnlyCheckObjects = makeValid(geometryToClipOnlyCheckObjects)
    # Actual clipping:
    clipped_result=gpd.clip(geometryToClipOnlyCheckObjects, mask_dissolved)
    clipped_result = clipped_result.explode(ignore_index=True)

    # Getting objects which were not clipped
    clipped_result = makeValid(clipped_result)
    clipped_result = clipped_result[clipped_result.geometry.type != 'Point']
    clipped_result = clipped_result[clipped_result.geometry.type != 'LineString']

    if dissolveBetween:
        clipped_result = clipped_result.dissolve(by=geometryToClipAttrsDissolve, as_index=False)

    clipped_result.reset_index(drop=True)
    geometryToClipOnlyCheckObjects.reset_index(drop=True)
    merged = geometryToClipOnlyCheckObjects.merge(clipped_result, how="outer", indicator=True, on=mergeIdField, suffixes=("", "_right"))
    not_clipped = merged[merged["_merge"] == "left_only"].copy()
    not_clipped.drop("_merge", axis=1, inplace=True)
    common_columns = set(geometryToClipOnlyCheckObjects.columns).intersection(not_clipped.columns)
    common_columns.add(geometryToClipOnlyCheckObjects.geometry.name)
    common_columns_list = list(common_columns)
    not_clipped = not_clipped[common_columns_list].copy()

    # Adding clipped results to objects which were not checked at all
    if geometryToClipCheckAttr is not None:
        retval = gpd.GeoDataFrame(pd.concat([geometryToClipNotCheckObjects, clipped_result], ignore_index=True))

    # Adding not clipped objects
    retval = gpd.GeoDataFrame(pd.concat([retval, not_clipped], ignore_index=True))
    retval = makeValid(retval)

    # Make a small buffer and take it back to get rid of intersection problems
    retval["geometry"] = retval.buffer(0.1)
    retval["geometry"] = retval.buffer(-0.1)

    for attr in geometryToClipAttrsDissolve:
        retval[attr] = retval[attr].fillna("")
    if geometryToClipAttrsDissolve:
        retval = retval.dissolve(by=geometryToClipAttrsDissolve, as_index=False)
    retval = retval.explode(ignore_index=True)

    return retval