/// Find token by binary searching cumulative probabilities.
pub(crate) fn find_token(transitions: &[(u16, u16)], value: u16) -> u16 {
    for (token_id, cumulative) in transitions {
        if *cumulative >= value {
            return *token_id;
        }
    }
    transitions.last().map(|(id, _)| *id).unwrap_or(0)
}
