//@flow
import * as React from 'react';
import { useContext } from 'react';
import { css } from '@emotion/core';

import DocumentProvider from '../document-provider.jsx';
import gettext from '../gettext.js';
import SearchIcon from '../icons/search.svg';

const strings = {
    placeholder: gettext('Search MDN')
};

const styles = {
    container: css({
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'center',
        padding: '2px 8px',
        border: 'solid #888 1px',
        borderRadius: 8,
        minWidth: 80,
        flex: '2 1'
    }),
    icon: css({
        fill: '#333',
        flex: '0 0 20px'
    }),
    input: css({
        // TODO: the !important declarations are used to override
        // stuff in the stylesheets. If we can simplify the
        // stylesheets, then maybe we can remove the importants
        borderWidth: '0 !important',
        fontSize: 16,
        fontWeight: 'bold !important',
        flex: '1 1 100px',
        minWidth: 60
    })
};

export default function Search() {
    const documentData = useContext(DocumentProvider.context);
    if (!documentData) {
        return null;
    }
    const { localeFromURL } = documentData;
    const WIKI_SITE_URL = window && window.mdn ? window.mdn.wikiSiteUrl : '';

    return (
        <form
            css={styles.container}
            id="nav-main-search"
            action={`${WIKI_SITE_URL}/${localeFromURL}/search`}
            method="get"
            role="search"
        >
            <SearchIcon css={styles.icon} />

            <input
                css={styles.input}
                type="search"
                id="main-q"
                name="q"
                placeholder={strings.placeholder}
            />
        </form>
    );
}
