document.addEventListener('DOMContentLoaded', () => {
    const teamAInput = document.getElementById('teamA');
    const teamBInput = document.getElementById('teamB');
    const mapNameInput = document.getElementById('mapName');
    const dataSourceSelect = document.getElementById('dataSource');
    const tournamentPagesInput = document.getElementById('tournamentPages');
    const tournamentPagesGroup = document.getElementById('tournamentPagesGroup');
    const teamFiltersInput = document.getElementById('teamFilters');
    const teamFiltersGroup = document.getElementById('teamFiltersGroup');

    const getTeamStatsBtn = document.getElementById('getTeamStatsBtn');
    const getMapSuggestionsBtn = document.getElementById('getMapSuggestionsBtn');
    const getBanSuggestionsBtn = document.getElementById('getBanSuggestionsBtn');

    const loadingIndicator = document.getElementById('loadingIndicator');

    const statsTeamNameSpan = document.getElementById('statsTeamName');
    const teamStatsOutput = document.getElementById('teamStatsOutput');

    const mapSuggestTeamsSpan = document.getElementById('mapSuggestTeams');
    const mapSuggestionsOutput = document.getElementById('mapSuggestionsOutput');

    const banSuggestTeamsMapSpan = document.getElementById('banSuggestTeamsMap');
    const banSuggestionsOutput = document.getElementById('banSuggestionsOutput');

    const API_BASE_URL = 'http://localhost:8000'; // Assuming FastAPI runs on port 8000

    dataSourceSelect.addEventListener('change', () => {
        if (dataSourceSelect.value === 'live') {
            tournamentPagesGroup.style.display = 'block';
            teamFiltersGroup.style.display = 'block';
        } else {
            tournamentPagesGroup.style.display = 'none';
            teamFiltersGroup.style.display = 'none';
        }
    });

    function showLoading(show) {
        loadingIndicator.style.display = show ? 'block' : 'none';
    }

    function displayError(element, error) {
        console.error('API Error:', error);
        let errorMessage = 'An error occurred.';
        if (error && error.detail) {
            errorMessage = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail);
        } else if (error && error.message) {
            errorMessage = error.message;
        }
        element.innerHTML = `<p class="error">Error: ${errorMessage}</p>`;
    }

    function buildApiUrl(path, params) {
        const url = new URL(`${API_BASE_URL}${path}`);
        url.searchParams.append('use_mock_data', dataSourceSelect.value === 'mock');
        if (dataSourceSelect.value === 'live') {
            const pages = tournamentPagesInput.value.split(',').map(p => p.trim()).filter(p => p);
            if (pages.length > 0) {
                pages.forEach(p => url.searchParams.append('tournament_pages', p));
            } else {
                 // For live data, tournament_pages might be required by some endpoints
                 // Handled by API if mandatory, but good to be aware.
            }
            const filters = teamFiltersInput.value.split(',').map(f => f.trim()).filter(f => f);
            if (filters.length > 0) {
                filters.forEach(f => url.searchParams.append('team_filters', f));
            }
        }
        for (const key in params) {
            if (params[key] !== undefined && params[key] !== null) {
                 if (Array.isArray(params[key])) {
                    params[key].forEach(val => url.searchParams.append(key, val));
                 } else {
                    url.searchParams.append(key, params[key]);
                 }
            }
        }
        return url.toString();
    }

    getTeamStatsBtn.addEventListener('click', async () => {
        const teamName = teamAInput.value.trim();
        if (!teamName) {
            alert('Please enter Team A name.');
            return;
        }

        statsTeamNameSpan.textContent = teamName;
        teamStatsOutput.innerHTML = '';
        showLoading(true);

        const url = buildApiUrl(`/team-stats/${teamName}`, {});

        try {
            const response = await fetch(url);
            const data = await response.json();
            showLoading(false);

            if (!response.ok) {
                displayError(teamStatsOutput, data);
                return;
            }

            let html = '<h4>Map Preferences (Sorted by Win Rate):</h4>';
            if (data.map_preferences && Object.keys(data.map_preferences).length > 0) {
                const sortedMaps = Object.entries(data.map_preferences)
                    .sort(([,a], [,b]) => b.win_rate - a.win_rate);
                html += '<ul>';
                sortedMaps.forEach(([map, stats]) => {
                    html += `<li>${map}: Played ${stats.times_played}, WR ${stats.win_rate.toFixed(1)}% (${stats.wins}W-${stats.losses}L), Round WR ${stats.round_win_rate.toFixed(1)}%</li>`;
                });
                html += '</ul>';
            } else {
                html += '<p>No map statistics available.</p>';
            }

            html += '<h4>Overall Operator Preferences (Top Picked):</h4>';
            // The API returns operator_preferences as { map_name_or_None: { op_name: OpStats } }
            // We need the overall stats, which are under the key `null` (becomes "null" string in JSON if not careful, or just None)
            // The current API model for TeamOperatorPreferences has `None` as key for overall.
            // FastAPI might serialize None as null.
            const overallOpPrefs = data.operator_preferences && (data.operator_preferences.null || data.operator_preferences[null] || data.operator_preferences["None"] || data.operator_preferences[undefined]);


            if (overallOpPrefs && Object.keys(overallOpPrefs).length > 0) {
                const sortedOps = Object.entries(overallOpPrefs)
                    .sort(([,a], [,b]) => b.times_picked - a.times_picked)
                    .slice(0, 10); // Show top 10
                html += '<ul>';
                sortedOps.forEach(([op, stats]) => {
                     if (stats.times_picked > 0) {
                        html += `<li>${op}: Picked ${stats.times_picked} (WR ${stats.win_rate_when_picked.toFixed(1)}%), Banned by team: ${stats.times_banned_by_team}, Banned by opp: ${stats.times_banned_by_opponent}</li>`;
                     }
                });
                html += '</ul>';
            } else {
                html += '<p>No overall operator statistics available.</p>';
            }
            teamStatsOutput.innerHTML = html;

        } catch (error) {
            showLoading(false);
            displayError(teamStatsOutput, error);
        }
    });

    getMapSuggestionsBtn.addEventListener('click', async () => {
        const teamA = teamAInput.value.trim();
        const teamB = teamBInput.value.trim();
        if (!teamA || !teamB) {
            alert('Please enter both Team A and Team B names.');
            return;
        }

        mapSuggestTeamsSpan.textContent = `${teamA} vs ${teamB}`;
        mapSuggestionsOutput.innerHTML = '';
        showLoading(true);

        const url = buildApiUrl("/suggest/maps", { team_a: teamA, team_b: teamB, num_suggestions: 3 });

        try {
            const response = await fetch(url);
            const suggestions = await response.json();
            showLoading(false);

            if (!response.ok) {
                displayError(mapSuggestionsOutput, suggestions);
                return;
            }

            if (suggestions.length === 0) {
                mapSuggestionsOutput.innerHTML = '<p>No map suggestions available for this matchup.</p>';
                return;
            }
            let html = '';
            suggestions.forEach((s, index) => {
                html += `<div class="suggestion-item">
                            <h4>Suggestion ${index + 1}: Play ${s.map_name}</h4>
                            <p><strong>Confidence:</strong> ${(s.confidence_score * 100).toFixed(1)}%</p>
                            <p class="reasoning"><strong>Reasoning:</strong> ${s.reasoning}</p>
                            <details><summary>Supporting Stats</summary><ul>`;
                for(const key in s.supporting_stats){
                    html += `<li><strong>${key.replace(/_/g, ' ')}:</strong> ${s.supporting_stats[key]}</li>`;
                }
                html += `</ul></details></div>`;
            });
            mapSuggestionsOutput.innerHTML = html;

        } catch (error) {
            showLoading(false);
            displayError(mapSuggestionsOutput, error);
        }
    });

    getBanSuggestionsBtn.addEventListener('click', async () => {
        const teamA = teamAInput.value.trim();
        const teamB = teamBInput.value.trim();
        const map = mapNameInput.value.trim();

        if (!teamA || !teamB || !map) {
            alert('Please enter Team A, Team B, and Map Name.');
            return;
        }

        banSuggestTeamsMapSpan.textContent = `${teamA} vs ${teamB} on ${map}`;
        banSuggestionsOutput.innerHTML = '';
        showLoading(true);

        const url = buildApiUrl("/suggest/operator-bans", { team_a: teamA, team_b: teamB, map_name: map, num_suggestions: 2 });

        try {
            const response = await fetch(url);
            const suggestions = await response.json();
            showLoading(false);

            if (!response.ok) {
                displayError(banSuggestionsOutput, suggestions);
                return;
            }

            if (suggestions.length === 0) {
                banSuggestionsOutput.innerHTML = '<p>No operator ban suggestions available for this scenario.</p>';
                return;
            }
            let html = '';
            suggestions.forEach((s, index) => {
                html += `<div class="suggestion-item">
                            <h4>Suggestion ${index + 1}: Ban ${s.operator_name}</h4>
                            <p><strong>Priority:</strong> ${s.priority}</p>
                            <p class="reasoning"><strong>Reasoning:</strong> ${s.reasoning}</p>
                            <details><summary>Supporting Stats</summary><ul>`;
                for(const key in s.supporting_stats){
                     html += `<li><strong>${key.replace(/_/g, ' ')}:</strong> ${s.supporting_stats[key]}</li>`;
                }
                html += `</ul></details></div>`;
            });
            banSuggestionsOutput.innerHTML = html;

        } catch (error) {
            showLoading(false);
            displayError(banSuggestionsOutput, error);
        }
    });
});
